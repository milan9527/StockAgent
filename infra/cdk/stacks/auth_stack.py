"""
Auth Stack - Cognito User Pool + SNS Notification Topic
"""
from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_cognito as cognito,
    aws_sns as sns,
)
from constructs import Construct


class AuthStack(Stack):
    def __init__(self, scope: Construct, id: str, project: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # ── Cognito User Pool ──
        self.user_pool = cognito.UserPool(self, "UserPool",
            user_pool_name=f"{project}-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(username=True, email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # App Client (for backend USER_PASSWORD_AUTH)
        self.user_pool_client = self.user_pool.add_client("WebAppClient",
            user_pool_client_name=f"{project}-webapp",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            generate_secret=False,
        )

        # ── SNS Notification Topic ──
        self.sns_topic = sns.Topic(self, "NotificationTopic",
            topic_name=f"{project}-notifications",
            display_name="Securities Trading Notifications",
        )

        # Outputs
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "SnsTopicArn", value=self.sns_topic.topic_arn)
