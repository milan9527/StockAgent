#!/usr/bin/env python3
"""
AWS 部署脚本 - 证券交易助手Agent平台
部署到 us-east-1，数据库和Redis安全组仅允许VPC内访问

使用方式:
  python infra/deploy_aws.py plan     # 预览部署计划
  python infra/deploy_aws.py deploy   # 执行部署
  python infra/deploy_aws.py status   # 查看状态
  python infra/deploy_aws.py destroy  # 销毁资源(谨慎)
"""
from __future__ import annotations

import sys
import json
import subprocess

REGION = "us-east-1"
PROJECT = "securities-trading"
TAG_KEY = "Project"
TAG_VAL = PROJECT


def run(cmd: str, check: bool = False) -> str:
    print(f"  $ {cmd[:120]}{'...' if len(cmd)>120 else ''}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0 and check:
        print(f"  ⚠ {r.stderr[:200]}")
    return r.stdout.strip()


def get_default_vpc():
    """获取默认VPC信息"""
    out = run(f"aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region {REGION} --output json")
    vpcs = json.loads(out).get("Vpcs", []) if out else []
    if not vpcs:
        print("  ❌ 未找到默认VPC，请手动指定VPC ID")
        return None, None, []
    vpc_id = vpcs[0]["VpcId"]
    cidr = vpcs[0]["CidrBlock"]
    # 获取子网
    out2 = run(f"aws ec2 describe-subnets --filters Name=vpc-id,Values={vpc_id} --region {REGION} --output json")
    subnets = json.loads(out2).get("Subnets", []) if out2 else []
    subnet_ids = [s["SubnetId"] for s in subnets]
    return vpc_id, cidr, subnet_ids


def plan():
    print("=" * 60)
    print("  证券交易助手Agent平台 - AWS部署计划")
    print(f"  区域: {REGION}")
    print("=" * 60)

    vpc_id, cidr, subnets = get_default_vpc()
    print(f"\n🔍 VPC: {vpc_id} ({cidr}), {len(subnets)} subnets")

    print("""
📦 将创建以下资源:

  ┌─────────────────────────────────────────────────────┐
  │  VPC Security Groups (仅VPC内访问)                    │
  │                                                     │
  │  sg-aurora: TCP 5432 ← VPC CIDR only               │
  │  sg-redis:  TCP 6379 ← VPC CIDR only               │
  └─────────────────────────────────────────────────────┘

  1. Amazon Aurora PostgreSQL Serverless v2
     - 集群: {project}-aurora
     - 安全组: sg-aurora (仅VPC内5432端口)
     - 引擎: aurora-postgresql 16.x
     - 容量: 0.5 - 16 ACU

  2. Amazon ElastiCache Redis Serverless
     - 名称: {project}-redis
     - 安全组: sg-redis (仅VPC内6379端口)

  3. AgentCore Runtime
     - Agent: SecuritiesTradingOrchestrator
     - 所有Agent运行在AgentCore Runtime

  4. AgentCore Memory (STM + LTM)
  5. AgentCore Registry (6个内置Skills)
  6. AgentCore Browser (Public + Web Bot Auth)
  7. AgentCore Code Interpreter (Public)
  8. AgentCore Observability (OTEL → CloudWatch)
  9. Bedrock Claude Sonnet 4.6

⚠️  前提条件:
  - AWS CLI 已配置
  - Bedrock 模型访问已开启
  - agentcore CLI 已安装

运行 'python infra/deploy_aws.py deploy' 开始部署
""".format(project=PROJECT))


def deploy():
    print("=" * 60)
    print("  开始部署到 AWS us-east-1")
    print("=" * 60)

    # 验证凭证
    print("\n🔑 验证AWS凭证...")
    identity = run(f"aws sts get-caller-identity --region {REGION} --output json")
    if not identity:
        print("  ❌ AWS凭证未配置"); return
    acct = json.loads(identity).get("Account", "")
    print(f"  ✅ Account: {acct}")

    # 获取VPC
    print("\n🔍 获取VPC信息...")
    vpc_id, cidr, subnets = get_default_vpc()
    if not vpc_id:
        return
    print(f"  VPC: {vpc_id} CIDR: {cidr}")
    print(f"  Subnets: {', '.join(subnets[:4])}")

    # ═══════════════════════════════════════════════════
    # 1. 创建安全组 (仅VPC内访问)
    # ═══════════════════════════════════════════════════
    print("\n🔒 1/9 创建安全组 (仅VPC内访问)...")

    # Aurora SG
    aurora_sg = run(f"""aws ec2 create-security-group \
        --group-name {PROJECT}-aurora-sg \
        --description "Aurora PostgreSQL - VPC internal only" \
        --vpc-id {vpc_id} \
        --region {REGION} \
        --output text --query GroupId 2>/dev/null""")
    if not aurora_sg:
        # 可能已存在
        aurora_sg = run(f"""aws ec2 describe-security-groups \
            --filters Name=group-name,Values={PROJECT}-aurora-sg Name=vpc-id,Values={vpc_id} \
            --region {REGION} --output text --query 'SecurityGroups[0].GroupId'""")
    if aurora_sg and aurora_sg != "None":
        print(f"  Aurora SG: {aurora_sg}")
        run(f"""aws ec2 authorize-security-group-ingress \
            --group-id {aurora_sg} \
            --protocol tcp --port 5432 \
            --cidr {cidr} \
            --region {REGION} 2>/dev/null""")
        run(f"""aws ec2 create-tags --resources {aurora_sg} \
            --tags Key={TAG_KEY},Value={TAG_VAL} Key=Name,Value={PROJECT}-aurora-sg \
            --region {REGION}""")
        print(f"  ✅ Aurora SG: TCP 5432 ← {cidr} (VPC only)")
    else:
        print("  ⚠ Aurora SG创建失败")
        aurora_sg = ""

    # Redis SG
    redis_sg = run(f"""aws ec2 create-security-group \
        --group-name {PROJECT}-redis-sg \
        --description "ElastiCache Redis - VPC internal only" \
        --vpc-id {vpc_id} \
        --region {REGION} \
        --output text --query GroupId 2>/dev/null""")
    if not redis_sg:
        redis_sg = run(f"""aws ec2 describe-security-groups \
            --filters Name=group-name,Values={PROJECT}-redis-sg Name=vpc-id,Values={vpc_id} \
            --region {REGION} --output text --query 'SecurityGroups[0].GroupId'""")
    if redis_sg and redis_sg != "None":
        print(f"  Redis SG: {redis_sg}")
        run(f"""aws ec2 authorize-security-group-ingress \
            --group-id {redis_sg} \
            --protocol tcp --port 6379 \
            --cidr {cidr} \
            --region {REGION} 2>/dev/null""")
        run(f"""aws ec2 create-tags --resources {redis_sg} \
            --tags Key={TAG_KEY},Value={TAG_VAL} Key=Name,Value={PROJECT}-redis-sg \
            --region {REGION}""")
        print(f"  ✅ Redis SG: TCP 6379 ← {cidr} (VPC only)")
    else:
        print("  ⚠ Redis SG创建失败")
        redis_sg = ""

    # ═══════════════════════════════════════════════════
    # 2. Aurora PostgreSQL
    # ═══════════════════════════════════════════════════
    print("\n📦 2/9 创建 Aurora PostgreSQL Serverless v2...")

    # DB Subnet Group
    subnet_list = " ".join(subnets[:4])
    run(f"""aws rds create-db-subnet-group \
        --db-subnet-group-name {PROJECT}-db-subnet \
        --db-subnet-group-description "Securities Trading DB Subnets" \
        --subnet-ids {subnet_list} \
        --region {REGION} 2>/dev/null""")

    sg_param = f"--vpc-security-group-ids {aurora_sg}" if aurora_sg else ""
    run(f"""aws rds create-db-cluster \
        --db-cluster-identifier {PROJECT}-aurora \
        --engine aurora-postgresql \
        --engine-version 16.4 \
        --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 \
        --master-username postgres \
        --master-user-password SecuritiesTrading2026Prod \
        --database-name securities_trading \
        --db-subnet-group-name {PROJECT}-db-subnet \
        {sg_param} \
        --tags Key={TAG_KEY},Value={TAG_VAL} \
        --region {REGION} \
        --output json 2>&1 | head -3""")

    run(f"""aws rds create-db-instance \
        --db-instance-identifier {PROJECT}-aurora-w1 \
        --db-cluster-identifier {PROJECT}-aurora \
        --engine aurora-postgresql \
        --db-instance-class db.serverless \
        --region {REGION} \
        --output json 2>&1 | head -3""")
    print("  ⏳ Aurora创建中 (约5-10分钟)...")

    # ═══════════════════════════════════════════════════
    # 3. ElastiCache Redis
    # ═══════════════════════════════════════════════════
    print("\n📦 3/9 创建 ElastiCache Redis Serverless...")
    sg_json = f'"SecurityGroupIds": ["{redis_sg}"],' if redis_sg else ""
    subnet_json = json.dumps(subnets[:4])
    run(f"""aws elasticache create-serverless-cache \
        --serverless-cache-name {PROJECT}-redis \
        --engine redis \
        --subnet-ids {' '.join(subnets[:4])} \
        {"--security-group-ids " + redis_sg if redis_sg else ""} \
        --tags Key={TAG_KEY},Value={TAG_VAL} \
        --region {REGION} \
        --output json 2>&1 | head -3""")
    print("  ⏳ Redis创建中...")

    # ═══════════════════════════════════════════════════
    # 4-8. AgentCore Resources
    # ═══════════════════════════════════════════════════
    print("\n📦 4/9 创建 AgentCore Memory...")
    run(f"""agentcore memory create securities_trading_memory \
        --description "证券交易助手记忆存储(STM+LTM)" \
        --strategies '[{{"summaryMemoryStrategy":{{"name":"SessionSummarizer","namespaces":["/summaries/{{actorId}}/{{sessionId}}"]}}}},{{"userPreferenceMemoryStrategy":{{"name":"InvestmentPreferenceLearner","namespaces":["/preferences/{{actorId}}"]}}}},{{"semanticMemoryStrategy":{{"name":"TradingKnowledgeExtractor","namespaces":["/knowledge/{{actorId}}"]}}}}]' \
        --region {REGION} --wait 2>&1 | tail -3""")

    print("\n📦 5/9 创建 AgentCore Browser (Public + Web Bot Auth)...")
    run(f"""aws bedrock-agentcore-control create-browser \
        --name SecuritiesTradingBrowser \
        --description "证券交易助手浏览器-获取最新市场数据" \
        --network-configuration networkMode=PUBLIC \
        --browser-signing enabled=true \
        --region {REGION} --output json 2>&1 | head -3""")

    print("\n📦 6/9 创建 AgentCore Code Interpreter (Public)...")
    run(f"""aws bedrock-agentcore-control create-code-interpreter \
        --name SecuritiesTradingCodeInterpreter \
        --description "证券交易助手代码解释器" \
        --network-configuration networkMode=PUBLIC \
        --region {REGION} --output json 2>&1 | head -3""")

    print("\n📦 7/9 创建 AgentCore Registry...")
    run(f"""aws bedrock-agentcore-control create-registry \
        --name SecuritiesTradingRegistry \
        --description "证券交易助手Skill注册中心" \
        --region {REGION} --output json 2>&1 | head -3""")

    print("\n📦 8/9 AgentCore Observability (默认启用)...")
    print("  ✅ OTEL遥测数据自动输出到CloudWatch")

    # ═══════════════════════════════════════════════════
    # 9. Deploy Agent to Runtime
    # ═══════════════════════════════════════════════════
    print("\n📦 9/9 部署Agent到AgentCore Runtime...")
    run("agentcore configure --entrypoint agents/orchestrator_agent.py --non-interactive 2>&1 | tail -3")
    run("agentcore launch 2>&1 | tail -5")

    # ═══════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  ✅ 部署命令已全部提交!")
    print("=" * 60)
    print(f"""
  安全组配置:
    Aurora SG ({aurora_sg}): TCP 5432 ← {cidr} (VPC only)
    Redis  SG ({redis_sg}): TCP 6379 ← {cidr} (VPC only)

  后续步骤:
    1. 等待Aurora和Redis就绪 (5-10分钟)
       python infra/deploy_aws.py status
    2. 获取endpoint更新 backend/env/aws.env
    3. 运行数据库迁移和种子数据
    4. 验证Agent: agentcore invoke '{{"prompt":"你好"}}'
""")


def status():
    print("=" * 60)
    print("  AWS 资源状态")
    print("=" * 60)

    print("\n🔒 安全组:")
    run(f"""aws ec2 describe-security-groups \
        --filters Name=group-name,Values={PROJECT}-aurora-sg,{PROJECT}-redis-sg \
        --region {REGION} \
        --query 'SecurityGroups[].{{Name:GroupName,ID:GroupId,Ingress:IpPermissions[0].{{Port:ToPort,CIDR:IpRanges[0].CidrIp}}}}' \
        --output table""")

    print("\n📊 Aurora PostgreSQL:")
    run(f"""aws rds describe-db-clusters \
        --db-cluster-identifier {PROJECT}-aurora \
        --region {REGION} \
        --query 'DBClusters[0].{{Status:Status,Endpoint:Endpoint,Port:Port,Engine:Engine}}' \
        --output table 2>&1""")

    print("\n📊 ElastiCache Redis:")
    run(f"""aws elasticache describe-serverless-caches \
        --serverless-cache-name {PROJECT}-redis \
        --region {REGION} \
        --query 'ServerlessCaches[0].{{Status:Status,Endpoint:Endpoint}}' \
        --output table 2>&1""")

    print("\n📊 AgentCore Runtime:")
    run("agentcore status 2>&1 | head -10")

    print("\n📊 AgentCore Memory:")
    run(f"agentcore memory list --region {REGION} 2>&1 | head -10")


def destroy():
    print("⚠️  即将销毁所有AWS资源，此操作不可逆!")
    confirm = input("输入 'YES' 确认: ")
    if confirm != "YES":
        print("已取消"); return

    print("\n�️ 销毁资源...")
    run("agentcore destroy --dry-run 2>&1 | head -10")
    run(f"aws rds delete-db-instance --db-instance-identifier {PROJECT}-aurora-w1 --skip-final-snapshot --region {REGION} 2>&1 | head -3")
    run(f"aws rds delete-db-cluster --db-cluster-identifier {PROJECT}-aurora --skip-final-snapshot --region {REGION} 2>&1 | head -3")
    run(f"aws elasticache delete-serverless-cache --serverless-cache-name {PROJECT}-redis --region {REGION} 2>&1 | head -3")
    print("  ⏳ 资源删除中...")


if __name__ == "__main__":
    cmds = {"plan": plan, "deploy": deploy, "status": status, "destroy": destroy}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("用法: python infra/deploy_aws.py [plan|deploy|status|destroy]")
        sys.exit(1)
    cmds[sys.argv[1]]()
