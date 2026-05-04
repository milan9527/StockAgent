"""
Data Stack - Aurora PostgreSQL Serverless v2 + ElastiCache Redis Serverless
"""
from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput, Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_elasticache as elasticache,
)
from constructs import Construct


class DataStack(Stack):
    def __init__(self, scope: Construct, id: str, project: str,
                 vpc: ec2.Vpc, db_sg: ec2.SecurityGroup,
                 redis_sg: ec2.SecurityGroup, **kwargs):
        super().__init__(scope, id, **kwargs)

        # ── Aurora PostgreSQL Serverless v2 ──
        self.db_cluster = rds.DatabaseCluster(self, "AuroraCluster",
            cluster_identifier=f"{project}-aurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_4,
            ),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=16,
            writer=rds.ClusterInstance.serverless_v2("Writer",
                publicly_accessible=False,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_sg],
            default_database_name="securities_trading",
            credentials=rds.Credentials.from_generated_secret("postgres",
                secret_name=f"{project}/aurora-credentials",
            ),
            removal_policy=RemovalPolicy.SNAPSHOT,
            backup=rds.BackupProps(retention=Duration.days(7)),
        )

        # ── ElastiCache Redis Serverless ──
        # Use CfnServerlessCache for serverless Redis
        private_subnet_ids = [s.subnet_id for s in vpc.isolated_subnets]

        self.redis_cache = elasticache.CfnServerlessCache(self, "RedisServerless",
            serverless_cache_name=f"{project}-redis",
            engine="redis",
            subnet_ids=private_subnet_ids,
            security_group_ids=[redis_sg.security_group_id],
        )

        # Outputs
        CfnOutput(self, "AuroraEndpoint", value=self.db_cluster.cluster_endpoint.hostname)
        CfnOutput(self, "AuroraPort", value=str(self.db_cluster.cluster_endpoint.port))
        CfnOutput(self, "AuroraSecretArn", value=self.db_cluster.secret.secret_arn)
        CfnOutput(self, "RedisName", value=self.redis_cache.serverless_cache_name)
