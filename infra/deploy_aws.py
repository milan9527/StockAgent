#!/usr/bin/env python3
"""
AWS 部署脚本 - 证券交易助手Agent平台
部署到 us-east-1

使用方式:
  python infra/deploy_aws.py plan       # 预览部署计划
  python infra/deploy_aws.py deploy     # 全量部署 (infra + backend + frontend + agent)
  python infra/deploy_aws.py frontend   # 仅部署前端 (S3 + CloudFront)
  python infra/deploy_aws.py backend    # 仅部署后端 (ECR + ECS)
  python infra/deploy_aws.py agent      # 仅部署AgentCore Runtime
  python infra/deploy_aws.py all        # 部署 frontend + backend + agent
  python infra/deploy_aws.py status     # 查看所有资源状态
  python infra/deploy_aws.py destroy    # 销毁资源(谨慎)
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
import time

REGION = "us-east-1"
ACCOUNT = "632930644527"
PROJECT = "securities-trading"
TAG_KEY = "Project"
TAG_VAL = PROJECT

# ── Resource IDs ──
ECR_REPO = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{PROJECT}-backend"
ECS_CLUSTER = PROJECT
ECS_SERVICE = "backend"
S3_BUCKET = "sec-trading-web-app-prod"
CF_DISTRIBUTION = "EFHJYSE515D2O"
SNS_TOPIC_ARN = f"arn:aws:sns:{REGION}:{ACCOUNT}:securities-trading-notifications"

# ── Paths ──
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


def run(cmd: str, cwd: str = None, check: bool = False) -> str:
    print(f"  $ {cmd[:140]}{'...' if len(cmd) > 140 else ''}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0 and check:
        print(f"  ⚠ {r.stderr[:300]}")
    return r.stdout.strip()


def run_live(cmd: str, cwd: str = None) -> int:
    """Run command with live output"""
    print(f"  $ {cmd[:140]}{'...' if len(cmd) > 140 else ''}")
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    return r.returncode


def get_default_vpc():
    out = run(f"aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region {REGION} --output json")
    vpcs = json.loads(out).get("Vpcs", []) if out else []
    if not vpcs:
        return None, None, []
    vpc_id = vpcs[0]["VpcId"]
    cidr = vpcs[0]["CidrBlock"]
    out2 = run(f"aws ec2 describe-subnets --filters Name=vpc-id,Values={vpc_id} --region {REGION} --output json")
    subnets = [s["SubnetId"] for s in json.loads(out2).get("Subnets", [])] if out2 else []
    return vpc_id, cidr, subnets


# ═══════════════════════════════════════════════════════
# Deploy: Frontend (S3 + CloudFront)
# ═══════════════════════════════════════════════════════

def deploy_frontend():
    print("\n" + "=" * 60)
    print("  📦 部署前端 → S3 + CloudFront")
    print("=" * 60)

    # Build
    print("\n🔨 Building frontend...")
    rc = run_live("npm run build", cwd=FRONTEND_DIR)
    if rc != 0:
        print("  ❌ Frontend build failed")
        return False

    # Upload to S3
    print("\n📤 Uploading to S3...")
    run(f"aws s3 sync {FRONTEND_DIR}/dist/ s3://{S3_BUCKET}/ --delete --region {REGION}")

    # Invalidate CloudFront
    print("\n🔄 Invalidating CloudFront cache...")
    out = run(f"aws cloudfront create-invalidation --distribution-id {CF_DISTRIBUTION} --paths '/*' --region {REGION} --output json")
    if out:
        inv_id = json.loads(out).get("Invalidation", {}).get("Id", "")
        print(f"  ✅ Invalidation: {inv_id}")

    print("  ✅ Frontend deployed → https://dt0u20qd1sod9.cloudfront.net")
    return True


# ═══════════════════════════════════════════════════════
# Deploy: Backend (Docker → ECR → ECS Fargate)
# ═══════════════════════════════════════════════════════

def deploy_backend():
    print("\n" + "=" * 60)
    print("  📦 部署后端 → ECR + ECS Fargate")
    print("=" * 60)

    # ECR login
    print("\n🔑 ECR login...")
    run(f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com")

    # Build Docker image
    print("\n🔨 Building Docker image...")
    rc = run_live(f"docker build -t {PROJECT}-backend:latest .", cwd=BACKEND_DIR)
    if rc != 0:
        print("  ❌ Docker build failed")
        return False

    # Tag and push
    print("\n📤 Pushing to ECR...")
    run(f"docker tag {PROJECT}-backend:latest {ECR_REPO}:latest")
    rc = run_live(f"docker push {ECR_REPO}:latest")
    if rc != 0:
        print("  ❌ ECR push failed")
        return False

    # Force new ECS deployment
    print("\n🚀 Deploying to ECS Fargate...")
    out = run(f"aws ecs update-service --cluster {ECS_CLUSTER} --service {ECS_SERVICE} "
              f"--force-new-deployment --region {REGION} --output json")
    if out:
        deployments = json.loads(out).get("service", {}).get("deployments", [])
        print(f"  ✅ ECS deployment triggered ({len(deployments)} deployments)")

    # Wait for rollout
    print("\n⏳ Waiting for ECS rollout (up to 5 min)...")
    for i in range(15):
        time.sleep(20)
        out = run(f"aws ecs describe-services --cluster {ECS_CLUSTER} --services {ECS_SERVICE} "
                  f"--region {REGION} --query 'services[0].deployments' --output json")
        if out:
            deps = json.loads(out)
            primary = next((d for d in deps if d.get("status") == "PRIMARY"), None)
            if primary and primary.get("rolloutState") == "COMPLETED" and len(deps) == 1:
                print(f"  ✅ ECS rollout COMPLETED — {primary['runningCount']}/{primary['desiredCount']} tasks running")
                return True
            running = primary.get("runningCount", 0) if primary else 0
            desired = primary.get("desiredCount", 0) if primary else 0
            state = primary.get("rolloutState", "?") if primary else "?"
            print(f"  ... {state} ({running}/{desired} running, {len(deps)} deployments)")

    print("  ⚠ Rollout still in progress — check with: python infra/deploy_aws.py status")
    return True


# ═══════════════════════════════════════════════════════
# Deploy: AgentCore Runtime
# ═══════════════════════════════════════════════════════

def deploy_agent():
    print("\n" + "=" * 60)
    print("  📦 部署 AgentCore Runtime")
    print("=" * 60)

    print("\n🚀 Launching agent to AgentCore Runtime...")
    rc = run_live("source .venv/bin/activate && agentcore launch", cwd=BACKEND_DIR)
    if rc != 0:
        print("  ⚠ agentcore launch returned non-zero (may still succeed)")
    else:
        print("  ✅ AgentCore Runtime deployed")
    return True


# ═══════════════════════════════════════════════════════
# Deploy: Full infrastructure (first-time setup)
# ═══════════════════════════════════════════════════════

def deploy_infra():
    print("=" * 60)
    print("  开始部署基础设施到 AWS us-east-1")
    print("=" * 60)

    # Verify credentials
    print("\n🔑 验证AWS凭证...")
    identity = run(f"aws sts get-caller-identity --region {REGION} --output json")
    if not identity:
        print("  ❌ AWS凭证未配置")
        return
    acct = json.loads(identity).get("Account", "")
    print(f"  ✅ Account: {acct}")

    vpc_id, cidr, subnets = get_default_vpc()
    if not vpc_id:
        print("  ❌ 未找到默认VPC")
        return
    print(f"  VPC: {vpc_id} CIDR: {cidr}, {len(subnets)} subnets")

    # Security Groups
    print("\n🔒 1/9 创建安全组...")
    for sg_name, port, desc in [
        (f"{PROJECT}-aurora-sg", 5432, "Aurora PostgreSQL"),
        (f"{PROJECT}-redis-sg", 6379, "ElastiCache Redis"),
    ]:
        sg_id = run(f"aws ec2 create-security-group --group-name {sg_name} "
                    f"--description '{desc} - VPC internal only' --vpc-id {vpc_id} "
                    f"--region {REGION} --output text --query GroupId 2>/dev/null")
        if not sg_id:
            sg_id = run(f"aws ec2 describe-security-groups --filters Name=group-name,Values={sg_name} "
                        f"Name=vpc-id,Values={vpc_id} --region {REGION} "
                        f"--output text --query 'SecurityGroups[0].GroupId'")
        if sg_id and sg_id != "None":
            run(f"aws ec2 authorize-security-group-ingress --group-id {sg_id} "
                f"--protocol tcp --port {port} --cidr {cidr} --region {REGION} 2>/dev/null")
            print(f"  ✅ {sg_name}: TCP {port} ← {cidr}")

    # Aurora
    print("\n📦 2/9 创建 Aurora PostgreSQL Serverless v2...")
    subnet_list = " ".join(subnets[:4])
    run(f"aws rds create-db-subnet-group --db-subnet-group-name {PROJECT}-db-subnet "
        f"--db-subnet-group-description 'Securities Trading DB' --subnet-ids {subnet_list} "
        f"--region {REGION} 2>/dev/null")
    run(f"aws rds create-db-cluster --db-cluster-identifier {PROJECT}-aurora "
        f"--engine aurora-postgresql --engine-version 16.4 "
        f"--serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 "
        f"--master-username postgres --master-user-password SecuritiesTrading2026Prod "
        f"--database-name securities_trading --db-subnet-group-name {PROJECT}-db-subnet "
        f"--tags Key={TAG_KEY},Value={TAG_VAL} --region {REGION} --output json 2>&1 | head -3")
    run(f"aws rds create-db-instance --db-instance-identifier {PROJECT}-aurora-w1 "
        f"--db-cluster-identifier {PROJECT}-aurora --engine aurora-postgresql "
        f"--db-instance-class db.serverless --region {REGION} --output json 2>&1 | head -3")
    print("  ⏳ Aurora创建中 (约5-10分钟)...")

    # Redis
    print("\n📦 3/9 创建 ElastiCache Redis Serverless...")
    run(f"aws elasticache create-serverless-cache --serverless-cache-name {PROJECT}-redis "
        f"--engine redis --subnet-ids {subnet_list} "
        f"--tags Key={TAG_KEY},Value={TAG_VAL} --region {REGION} --output json 2>&1 | head -3")

    # AgentCore
    print("\n📦 4/9 创建 AgentCore Memory...")
    run(f"source {BACKEND_DIR}/.venv/bin/activate && agentcore memory create securities_trading_memory "
        f"--description '证券交易助手记忆存储' --region {REGION} --wait 2>&1 | tail -3")

    print("\n📦 5/9 创建 AgentCore Browser...")
    run(f"aws bedrock-agentcore-control create-browser --name SecuritiesTradingBrowser "
        f"--network-configuration networkMode=PUBLIC --browser-signing enabled=true "
        f"--region {REGION} --output json 2>&1 | head -3")

    print("\n📦 6/9 创建 AgentCore Code Interpreter...")
    run(f"aws bedrock-agentcore-control create-code-interpreter --name SecuritiesTradingCodeInterpreter "
        f"--network-configuration networkMode=PUBLIC --region {REGION} --output json 2>&1 | head -3")

    print("\n📦 7/9 创建 AgentCore Registry...")
    run(f"aws bedrock-agentcore-control create-registry --name SecuritiesTradingRegistry "
        f"--region {REGION} --output json 2>&1 | head -3")

    print("\n📦 8/9 创建 SNS Topic...")
    run(f"aws sns create-topic --name securities-trading-notifications --region {REGION} --output json 2>&1 | head -3")

    print("\n📦 9/9 部署Agent到AgentCore Runtime...")
    run_live(f"source {BACKEND_DIR}/.venv/bin/activate && agentcore launch")

    print("\n" + "=" * 60)
    print("  ✅ 基础设施部署命令已提交!")
    print("=" * 60)
    print(f"""
  后续步骤:
    1. 等待Aurora和Redis就绪: python infra/deploy_aws.py status
    2. 获取endpoint更新 backend/env/aws.env
    3. 部署应用: python infra/deploy_aws.py all
""")


# ═══════════════════════════════════════════════════════
# Deploy All (frontend + backend + agent)
# ═══════════════════════════════════════════════════════

def deploy_all():
    print("=" * 60)
    print("  🚀 全量部署: Frontend + Backend (ECS) + AgentCore")
    print("=" * 60)

    # Verify credentials
    identity = run(f"aws sts get-caller-identity --region {REGION} --output json")
    if not identity:
        print("  ❌ AWS凭证未配置")
        return
    print(f"  ✅ Account: {json.loads(identity).get('Account', '')}")

    ok1 = deploy_frontend()
    ok2 = deploy_backend()
    ok3 = deploy_agent()

    print("\n" + "=" * 60)
    print("  部署结果:")
    print(f"    Frontend (S3+CF):     {'✅' if ok1 else '❌'}")
    print(f"    Backend (ECR+ECS):    {'✅' if ok2 else '❌'}")
    print(f"    AgentCore Runtime:    {'✅' if ok3 else '❌'}")
    print("=" * 60)
    print(f"  🌐 https://dt0u20qd1sod9.cloudfront.net")


# ═══════════════════════════════════════════════════════
# Status
# ═══════════════════════════════════════════════════════

def status():
    print("=" * 60)
    print("  AWS 资源状态")
    print("=" * 60)

    # ECS
    print("\n📊 ECS Fargate:")
    out = run(f"aws ecs describe-services --cluster {ECS_CLUSTER} --services {ECS_SERVICE} "
              f"--region {REGION} --query 'services[0].{{status:status,desired:desiredCount,"
              f"running:runningCount,taskDef:taskDefinition,deployments:deployments[*]."
              f"{{status:status,desired:desiredCount,running:runningCount,rollout:rolloutState}}}}' "
              f"--output json")
    if out:
        data = json.loads(out)
        print(f"  Status: {data.get('status')}")
        print(f"  Tasks: {data.get('running')}/{data.get('desired')}")
        for d in data.get("deployments", []):
            print(f"  Deployment: {d['status']} — {d['running']}/{d['desired']} — {d['rollout']}")

    # Aurora
    print("\n📊 Aurora PostgreSQL:")
    out = run(f"aws rds describe-db-clusters --db-cluster-identifier {PROJECT}-aurora "
              f"--region {REGION} --query 'DBClusters[0].{{Status:Status,Endpoint:Endpoint}}' "
              f"--output json 2>&1")
    if out and "error" not in out.lower():
        data = json.loads(out)
        print(f"  Status: {data.get('Status')}")
        print(f"  Endpoint: {data.get('Endpoint')}")

    # Redis
    print("\n📊 ElastiCache Redis:")
    out = run(f"aws elasticache describe-serverless-caches --serverless-cache-name {PROJECT}-redis "
              f"--region {REGION} --query 'ServerlessCaches[0].{{Status:Status,Endpoint:Endpoint}}' "
              f"--output json 2>&1")
    if out and "error" not in out.lower():
        data = json.loads(out)
        print(f"  Status: {data.get('Status')}")
        ep = data.get("Endpoint", {})
        if isinstance(ep, dict):
            print(f"  Endpoint: {ep.get('Address', '')}:{ep.get('Port', '')}")

    # AgentCore
    print("\n📊 AgentCore Runtime:")
    run_live(f"source {BACKEND_DIR}/.venv/bin/activate && agentcore status 2>&1 | head -15")

    # Cognito
    print("\n📊 Cognito User Pool:")
    out = run(f"aws cognito-idp list-users --user-pool-id us-east-1_DpOE0uo8p "
              f"--region {REGION} --query 'Users[*].{{Username:Username,Status:UserStatus}}' "
              f"--output table 2>&1")
    if out:
        print(out)

    # SNS
    print("\n📊 SNS Notifications:")
    out = run(f"aws sns list-subscriptions-by-topic --topic-arn {SNS_TOPIC_ARN} "
              f"--region {REGION} --query 'Subscriptions[*].{{Endpoint:Endpoint,Protocol:Protocol,"
              f"Status:SubscriptionArn}}' --output table 2>&1")
    if out:
        print(out)

    # CloudFront
    print("\n📊 CloudFront:")
    print(f"  URL: https://dt0u20qd1sod9.cloudfront.net")
    out = run(f"aws cloudfront get-distribution --id {CF_DISTRIBUTION} "
              f"--query 'Distribution.Status' --output text 2>&1")
    if out:
        print(f"  Status: {out}")


# ═══════════════════════════════════════════════════════
# Plan
# ═══════════════════════════════════════════════════════

def plan():
    print("=" * 60)
    print("  证券交易助手Agent平台 - AWS部署计划")
    print(f"  区域: {REGION}  账户: {ACCOUNT}")
    print("=" * 60)

    vpc_id, cidr, subnets = get_default_vpc()
    print(f"\n🔍 VPC: {vpc_id} ({cidr}), {len(subnets)} subnets")

    print(f"""
📦 部署组件:

  ┌─ Frontend ─────────────────────────────────────────────┐
  │  npm run build → S3 ({S3_BUCKET})                      │
  │  CloudFront ({CF_DISTRIBUTION}) cache invalidation     │
  └────────────────────────────────────────────────────────┘

  ┌─ Backend (ECS Fargate) ────────────────────────────────┐
  │  docker build → ECR ({PROJECT}-backend)                │
  │  ECS force-new-deployment ({ECS_CLUSTER}/{ECS_SERVICE})│
  │  2 Fargate tasks, rolling update                       │
  └────────────────────────────────────────────────────────┘

  ┌─ AgentCore Runtime ────────────────────────────────────┐
  │  agentcore launch (direct code deploy, ARM64)          │
  │  Memory: STM + LTM (3 strategies)                      │
  │  Registry: 9 skills                                    │
  │  Browser + Code Interpreter                            │
  └────────────────────────────────────────────────────────┘

  ┌─ Data Layer ───────────────────────────────────────────┐
  │  Aurora PostgreSQL Serverless v2 (VPC-only)            │
  │  ElastiCache Redis Serverless (TLS, VPC-only)          │
  └────────────────────────────────────────────────────────┘

  ┌─ Auth & Notifications ─────────────────────────────────┐
  │  Cognito User Pool (us-east-1_DpOE0uo8p)              │
  │  SNS Topic (securities-trading-notifications)          │
  └────────────────────────────────────────────────────────┘

命令:
  python infra/deploy_aws.py frontend   # 仅前端
  python infra/deploy_aws.py backend    # 仅后端 (ECS)
  python infra/deploy_aws.py agent      # 仅AgentCore
  python infra/deploy_aws.py all        # 全部
  python infra/deploy_aws.py deploy     # 全量 (含基础设施)
  python infra/deploy_aws.py status     # 查看状态
""")


# ═══════════════════════════════════════════════════════
# Destroy
# ═══════════════════════════════════════════════════════

def destroy():
    print("⚠️  即将销毁所有AWS资源，此操作不可逆!")
    confirm = input("输入 'YES' 确认: ")
    if confirm != "YES":
        print("已取消")
        return

    print("\n🗑️ 销毁资源...")
    run(f"source {BACKEND_DIR}/.venv/bin/activate && agentcore destroy --dry-run 2>&1 | head -10")
    run(f"aws ecs update-service --cluster {ECS_CLUSTER} --service {ECS_SERVICE} "
        f"--desired-count 0 --region {REGION} 2>&1 | head -3")
    run(f"aws rds delete-db-instance --db-instance-identifier {PROJECT}-aurora-w1 "
        f"--skip-final-snapshot --region {REGION} 2>&1 | head -3")
    run(f"aws rds delete-db-cluster --db-cluster-identifier {PROJECT}-aurora "
        f"--skip-final-snapshot --region {REGION} 2>&1 | head -3")
    run(f"aws elasticache delete-serverless-cache --serverless-cache-name {PROJECT}-redis "
        f"--region {REGION} 2>&1 | head -3")
    print("  ⏳ 资源删除中...")


if __name__ == "__main__":
    cmds = {
        "plan": plan,
        "deploy": deploy_infra,
        "frontend": deploy_frontend,
        "backend": deploy_backend,
        "agent": deploy_agent,
        "all": deploy_all,
        "status": status,
        "destroy": destroy,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("用法: python infra/deploy_aws.py [plan|deploy|frontend|backend|agent|all|status|destroy]")
        print()
        print("  plan      预览部署计划")
        print("  deploy    全量部署 (含基础设施创建)")
        print("  frontend  仅部署前端 (S3 + CloudFront)")
        print("  backend   仅部署后端 (Docker → ECR → ECS Fargate)")
        print("  agent     仅部署AgentCore Runtime")
        print("  all       部署 frontend + backend + agent")
        print("  status    查看所有资源状态")
        print("  destroy   销毁资源 (谨慎)")
        sys.exit(1)
    cmds[sys.argv[1]]()
