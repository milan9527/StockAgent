"""
Skill管理路由 - 直接管理AgentCore Registry记录
所有skill数据来自Registry, 本地只缓存builtin skill定义
"""
from __future__ import annotations

import os
import json as _json
import time
import traceback
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, CustomSkill
from api.auth import get_current_user
from api.schemas import CustomSkillCreate, CustomSkillResponse
from config.settings import get_settings

router = APIRouter(prefix="/api/skills", tags=["Skills管理"])
_settings = get_settings()

REGISTRY_ID = _settings.AGENTCORE_REGISTRY_ID
AWS_REGION = _settings.AWS_REGION


def _get_ctrl_client():
    import boto3
    return boto3.client("bedrock-agentcore-control", region_name=AWS_REGION)


def _get_dp_client():
    import boto3
    return boto3.client("bedrock-agentcore", region_name=AWS_REGION)


# ═══════════════════════════════════════════════════════
# Builtin skill -> Registry name mapping
# ═══════════════════════════════════════════════════════
BUILTIN_SKILLS = {
    "market-data-skill": {"name": "行情数据技能", "type": "market", "file": "agents/skills/market_data_skill.py"},
    "analysis-skill": {"name": "投资分析技能", "type": "analysis", "file": "agents/skills/analysis_skill.py"},
    "web-fetch-skill": {"name": "Web信息获取技能", "type": "web", "file": "agents/skills/web_fetch_skill.py"},
    "trading-skill": {"name": "交易技能", "type": "trading", "file": "agents/skills/trading_skill.py"},
    "quant-skill": {"name": "量化交易技能", "type": "quant", "file": "agents/skills/quant_skill.py"},
    "notification-skill": {"name": "通知技能", "type": "notification", "file": "agents/skills/notification_skill.py"},
    "crawler-skill": {"name": "专业财经爬虫技能", "type": "web", "file": "agents/skills/crawler_skill.py"},
    "browser-crawler-skill": {"name": "浏览器爬虫技能", "type": "web", "file": ""},
    "code-interpreter-skill": {"name": "代码执行技能", "type": "quant", "file": ""},
}


# ═══════════════════════════════════════════════════════
# Registry Records (核心API)
# ═══════════════════════════════════════════════════════

@router.get("/registry")
async def list_registry_records(current_user: User = Depends(get_current_user)):
    """列出AgentCore Registry中所有记录(去重)"""
    if not REGISTRY_ID:
        return {"records": [], "error": "Registry未配置"}
    try:
        client = _get_ctrl_client()
        resp = client.list_registry_records(registryId=REGISTRY_ID, maxResults=50)
        # Deduplicate by name, keep APPROVED over others
        by_name = {}
        for r in resp.get("registryRecords", []):
            name = r.get("name", "")
            existing = by_name.get(name)
            if not existing or (r.get("status") == "APPROVED" and existing.get("status") != "APPROVED"):
                by_name[name] = r

        records = []
        for name, r in by_name.items():
            builtin = BUILTIN_SKILLS.get(name, {})
            records.append({
                "record_id": r.get("recordId", ""),
                "name": name,
                "display_name": builtin.get("name", name),
                "status": r.get("status", ""),
                "version": r.get("recordVersion", ""),
                "description": r.get("description", ""),
                "type": r.get("descriptorType", ""),
                "skill_type": builtin.get("type", "external"),
                "is_builtin": name in BUILTIN_SKILLS,
                "created_at": str(r.get("createdAt", "")),
                "updated_at": str(r.get("updatedAt", "")),
            })
        # Sort: builtin first, then by name
        records.sort(key=lambda x: (0 if x["is_builtin"] else 1, x["name"]))
        return {"records": records, "registry_id": REGISTRY_ID}
    except Exception as e:
        return {"records": [], "error": str(e)[:200]}


@router.get("/registry/{record_id}")
async def get_registry_record(record_id: str, current_user: User = Depends(get_current_user)):
    """获取Registry记录详情(含完整内容)"""
    if not REGISTRY_ID:
        return {"error": "Registry未配置"}
    try:
        client = _get_ctrl_client()
        r = client.get_registry_record(registryId=REGISTRY_ID, recordId=record_id)
        record = r.get("registryRecord", r)

        # Extract skill content
        content = ""
        descriptors = record.get("descriptors", {})
        agent_skills = descriptors.get("agentSkills", {})
        skill_md = agent_skills.get("skillMd", {})
        content = skill_md.get("inlineContent", "")

        return {
            "record_id": record.get("recordId", record_id),
            "name": record.get("name", ""),
            "status": record.get("status", ""),
            "version": record.get("recordVersion", ""),
            "description": record.get("description", ""),
            "type": record.get("descriptorType", ""),
            "content": content,
            "raw": _json.dumps(descriptors, default=str, indent=2)[:5000],
        }
    except Exception as e:
        return {"error": str(e)[:200]}


class CreateRecordRequest(BaseModel):
    name: str
    description: str = ""
    content: str = ""  # SKILL.md content
    version: str = "1.0.0"


@router.post("/registry")
async def create_registry_record(request: CreateRecordRequest, current_user: User = Depends(get_current_user)):
    """创建新的Registry记录"""
    if not REGISTRY_ID:
        return {"error": "Registry未配置"}
    try:
        client = _get_ctrl_client()
        r = client.create_registry_record(
            registryId=REGISTRY_ID,
            name=request.name,
            descriptorType="AGENT_SKILLS",
            descriptors={"agentSkills": {"skillMd": {"inlineContent": request.content or f"---\nname: {request.name}\ndescription: {request.description}\n---\n\n# {request.name}\n\n{request.description}\n"}}},
            recordVersion=request.version,
            description=request.description[:200],
        )
        record_id = r["recordArn"].split("/")[-1]
        # Auto-submit for approval
        time.sleep(1)
        try:
            client.submit_registry_record_for_approval(registryId=REGISTRY_ID, recordId=record_id)
        except Exception:
            pass
        return {"record_id": record_id, "name": request.name, "status": "PENDING_APPROVAL"}
    except Exception as e:
        return {"error": str(e)[:200]}


@router.put("/registry/{record_id}/status")
async def update_record_status(record_id: str, status: str = "APPROVED", current_user: User = Depends(get_current_user)):
    """更新Registry记录状态 (APPROVED/REJECTED/DEPRECATED)"""
    if not REGISTRY_ID:
        return {"error": "Registry未配置"}
    try:
        client = _get_ctrl_client()
        client.update_registry_record_status(registryId=REGISTRY_ID, recordId=record_id, status=status)
        return {"success": True, "record_id": record_id, "status": status}
    except Exception as e:
        return {"error": str(e)[:200]}


@router.delete("/registry/{record_id}")
async def delete_registry_record(record_id: str, current_user: User = Depends(get_current_user)):
    """删除Registry记录"""
    if not REGISTRY_ID:
        return {"error": "Registry未配置"}
    try:
        client = _get_ctrl_client()
        client.delete_registry_record(registryId=REGISTRY_ID, recordId=record_id)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
# Import from GitHub URL
# ═══════════════════════════════════════════════════════

class ImportGithubRequest(BaseModel):
    url: str


@router.post("/import-github")
async def import_from_github(request: ImportGithubRequest, current_user: User = Depends(get_current_user)):
    """从GitHub URL导入Skill到Registry"""
    import httpx, re

    url = request.url
    try:
        # Convert GitHub URL to raw content
        raw_url = url
        if "github.com" in url and "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        elif "github.com" in url and "/tree/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/") + "/SKILL.md"

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(raw_url, headers={"User-Agent": "AgentSkillImporter/1.0"})
            resp.raise_for_status()
            content = resp.text

        # Parse name from YAML frontmatter
        name = ""
        desc = ""
        if "---" in content:
            parts = content.split("---")
            if len(parts) >= 3:
                name_match = re.search(r"name:\s*(.+)", parts[1])
                desc_match = re.search(r"description:\s*(.+)", parts[1])
                if name_match:
                    name = name_match.group(1).strip().strip('"').strip("'")
                if desc_match:
                    desc = desc_match.group(1).strip().strip('"').strip("'")[:200]

        if not name:
            name = url.split("/")[-1].replace(".md", "").replace("_", "-").lower()

        # Publish to Registry
        if not REGISTRY_ID:
            return {"error": "Registry未配置"}

        ctrl = _get_ctrl_client()
        r = ctrl.create_registry_record(
            registryId=REGISTRY_ID, name=name,
            descriptorType="AGENT_SKILLS",
            descriptors={"agentSkills": {"skillMd": {"inlineContent": content}}},
            recordVersion="1.0.0", description=desc or f"Imported from {url}"[:200],
        )
        record_id = r["recordArn"].split("/")[-1]
        time.sleep(1)
        try:
            ctrl.submit_registry_record_for_approval(registryId=REGISTRY_ID, recordId=record_id)
        except Exception:
            pass

        return {"record_id": record_id, "name": name, "status": "PENDING_APPROVAL", "content_length": len(content)}
    except Exception as e:
        return {"error": f"导入失败: {str(e)[:200]}"}


# ═══════════════════════════════════════════════════════
# Update all builtin skills in Registry
# ═══════════════════════════════════════════════════════

@router.post("/update-registry")
async def update_all_registry_records(current_user: User = Depends(get_current_user)):
    """读取所有SKILL.md并更新Registry记录"""
    if not REGISTRY_ID:
        return {"error": "Registry未配置"}

    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agents", "skills")
    ctrl = _get_ctrl_client()
    results = []

    for reg_name in BUILTIN_SKILLS:
        skill_md_path = os.path.join(base_dir, reg_name, "SKILL.md")
        if not os.path.exists(skill_md_path):
            results.append({"name": reg_name, "status": "SKIP", "reason": "No SKILL.md"})
            continue

        with open(skill_md_path) as f:
            md_content = f.read()

        desc = BUILTIN_SKILLS[reg_name].get("name", reg_name)[:200]

        try:
            # Find existing record
            dp = _get_dp_client()
            arn = f"arn:aws:bedrock-agentcore:{AWS_REGION}:632930644527:registry/{REGISTRY_ID}"
            search = dp.search_registry_records(registryIds=[arn], searchQuery=reg_name, maxResults=5)
            existing = None
            for rec in search.get("registryRecords", []):
                if rec.get("name") == reg_name:
                    existing = rec
                    break

            if existing and existing.get("recordId"):
                # Update existing
                try:
                    ctrl.update_registry_record(
                        registryId=REGISTRY_ID, recordId=existing["recordId"],
                        descriptors={"agentSkills": {"skillMd": {"inlineContent": md_content}}},
                        recordVersion="5.0.0", description=desc,
                    )
                    results.append({"name": reg_name, "status": "UPDATED", "record_id": existing["recordId"]})
                except Exception:
                    # If update fails, create new
                    r = ctrl.create_registry_record(
                        registryId=REGISTRY_ID, name=reg_name, descriptorType="AGENT_SKILLS",
                        descriptors={"agentSkills": {"skillMd": {"inlineContent": md_content}}},
                        recordVersion="5.0.0", description=desc,
                    )
                    rid = r["recordArn"].split("/")[-1]
                    time.sleep(1)
                    try:
                        ctrl.submit_registry_record_for_approval(registryId=REGISTRY_ID, recordId=rid)
                    except Exception:
                        pass
                    results.append({"name": reg_name, "status": "CREATED", "record_id": rid})
            else:
                # Create new
                r = ctrl.create_registry_record(
                    registryId=REGISTRY_ID, name=reg_name, descriptorType="AGENT_SKILLS",
                    descriptors={"agentSkills": {"skillMd": {"inlineContent": md_content}}},
                    recordVersion="5.0.0", description=desc,
                )
                rid = r["recordArn"].split("/")[-1]
                time.sleep(1)
                try:
                    ctrl.submit_registry_record_for_approval(registryId=REGISTRY_ID, recordId=rid)
                except Exception:
                    pass
                results.append({"name": reg_name, "status": "CREATED", "record_id": rid})
        except Exception as e:
            results.append({"name": reg_name, "status": "ERROR", "error": str(e)[:150]})

    return {"results": results, "total": len(results)}


# ═══════════════════════════════════════════════════════
# AI自然语言创建Skill
# ═══════════════════════════════════════════════════════

class AICreateSkillRequest(BaseModel):
    description: str
    skill_type: str = "analysis"


@router.post("/ai-create")
async def ai_create_skill(request: AICreateSkillRequest, current_user: User = Depends(get_current_user)):
    """用自然语言描述创建Skill, LLM生成SKILL.md"""
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

        prompt = f"""根据用户描述生成一个Agent Skill的SKILL.md文件。

格式要求(agentskills.io规范):
---
name: skill-name-lowercase
description: >
  详细描述skill功能和使用场景
license: Apache-2.0
metadata:
  version: "1.0.0"
  category: {request.skill_type}
allowed-tools: tool1 tool2
---

# Skill Name

## Tools
### tool1(param1, param2)
描述

## Examples
- 示例用法

用户描述: {request.description}

只输出SKILL.md内容:"""

        body = _json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(modelId=_settings.LLM_MODEL_ID, body=body)
        content = _json.loads(resp["body"].read()).get("content", [{}])[0].get("text", "")

        # Extract name from generated content
        import re
        name_match = re.search(r"name:\s*(.+)", content)
        name = name_match.group(1).strip() if name_match else "custom-skill"

        return {"name": name, "content": content, "skill_type": request.skill_type}
    except Exception as e:
        return {"error": f"AI生成失败: {str(e)[:200]}"}


# ═══════════════════════════════════════════════════════
# Builtin skill source code
# ═══════════════════════════════════════════════════════

@router.get("/code/{skill_name}")
async def get_skill_source(skill_name: str, current_user: User = Depends(get_current_user)):
    """获取builtin skill的Python源码和SKILL.md"""
    builtin = BUILTIN_SKILLS.get(skill_name)
    if not builtin:
        return {"error": "Skill not found"}

    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    code = ""
    if builtin.get("file"):
        try:
            with open(os.path.join(base, builtin["file"])) as f:
                code = f.read()
        except Exception:
            pass

    skill_md = ""
    md_path = os.path.join(base, "agents", "skills", skill_name, "SKILL.md")
    try:
        with open(md_path) as f:
            skill_md = f.read()
    except Exception:
        pass

    return {"name": skill_name, "display_name": builtin["name"], "code": code, "skill_md": skill_md}


# ═══════════════════════════════════════════════════════
# Legacy endpoints (backward compatibility)
# ═══════════════════════════════════════════════════════

@router.get("/builtin")
async def get_builtin_skills(current_user: User = Depends(get_current_user)):
    """获取内置Skills列表"""
    skills = []
    for reg_name, info in BUILTIN_SKILLS.items():
        skills.append({
            "id": f"builtin-{reg_name.replace('-skill', '')}",
            "name": info["name"],
            "registry_name": reg_name,
            "skill_type": info["type"],
            "description": info["name"],
            "tools": [],
            "source": "builtin",
            "version": "5.0.0",
            "registry_status": "",
        })
    return {"skills": skills}


@router.get("/all")
async def get_all_skills(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取所有Skills"""
    builtin = []
    for reg_name, info in BUILTIN_SKILLS.items():
        builtin.append({
            "id": f"builtin-{reg_name.replace('-skill', '')}",
            "name": info["name"],
            "registry_name": reg_name,
            "skill_type": info["type"],
            "description": info["name"],
            "tools": [],
            "source": "builtin",
            "version": "5.0.0",
        })

    result = await db.execute(select(CustomSkill).where(CustomSkill.user_id == current_user.id))
    custom = [{"id": str(s.id), "name": s.name, "skill_type": s.skill_type, "description": s.description,
               "tools": [], "source": "custom", "version": s.version, "code": s.code} for s in result.scalars().all()]

    return {"builtin": builtin, "custom": custom, "total": len(builtin) + len(custom)}


# Legacy CRUD for custom skills (DB-based)
@router.post("/", response_model=CustomSkillResponse)
async def create_skill(skill: CustomSkillCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_skill = CustomSkill(user_id=current_user.id, name=skill.name, description=skill.description,
                            skill_type=skill.skill_type, code=skill.code, parameters_schema=skill.parameters_schema)
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return CustomSkillResponse(id=str(new_skill.id), name=new_skill.name, description=new_skill.description,
                               skill_type=new_skill.skill_type, code=new_skill.code, is_published=new_skill.is_published, version=new_skill.version)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CustomSkill).where(CustomSkill.id == skill_id, CustomSkill.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Skill不存在")
    await db.delete(existing)
    await db.commit()
    return {"message": "Skill已删除"}


# MCP placeholder
@router.get("/mcp")
async def get_mcp_servers(current_user: User = Depends(get_current_user)):
    return {"servers": []}
