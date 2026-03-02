#!/bin/bash
set -euo pipefail

# ==============================================================
# MediDocsReferral AWS デプロイスクリプト
# 使い方: ./scripts/deploy.sh [--account-id ACCOUNT_ID] [--tag TAG]
# ==============================================================

REGION="ap-northeast-1"
ECR_REPO="medidocs-referral"
CLUSTER="medidocs-cluster"
SERVICE="medidocs-referral-service"
TAG="${TAG:-latest}"
ACCOUNT_ID="${ACCOUNT_ID:-}"

# 引数パース
while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id) ACCOUNT_ID="$2"; shift 2 ;;
    --tag)        TAG="$2";        shift 2 ;;
    *) echo "不明なオプション: $1"; exit 1 ;;
  esac
done

# ACCOUNT_ID未設定の場合はAWS CLIから取得
if [[ -z "$ACCOUNT_ID" ]]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

echo "=== デプロイ開始 ==="
echo "ACCOUNT_ID: ${ACCOUNT_ID}"
echo "ECR URI:    ${ECR_URI}:${TAG}"
echo "CLUSTER:    ${CLUSTER}"
echo "SERVICE:    ${SERVICE}"
echo ""

# 1. ECRにログイン
echo "--- ECR ログイン ---"
aws ecr get-login-password --region "${REGION}" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# 2. Dockerイメージをビルド
echo "--- Docker ビルド ---"
docker build \
  --platform linux/amd64 \
  -t "${ECR_REPO}:${TAG}" \
  "$(dirname "$0")/.."

# 3. タグ付け
docker tag "${ECR_REPO}:${TAG}" "${ECR_URI}:${TAG}"

# 4. ECRにプッシュ
echo "--- ECR プッシュ ---"
docker push "${ECR_URI}:${TAG}"

# 5. ECSサービスを更新
echo "--- ECS サービス更新 ---"
aws ecs update-service \
  --region "${REGION}" \
  --cluster "${CLUSTER}" \
  --service "${SERVICE}" \
  --force-new-deployment \
  --output json \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"サービス更新完了: {d['service']['serviceName']}\")"

echo ""
echo "=== デプロイ完了 ==="
echo "ECSサービスの更新状況は以下のコマンドで確認できます:"
echo "  aws ecs describe-services --cluster ${CLUSTER} --services ${SERVICE} --region ${REGION}"
