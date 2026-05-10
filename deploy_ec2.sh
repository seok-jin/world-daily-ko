#!/usr/bin/env bash
# EC2 (3.37.118.119) 배포 스크립트 — scp 방식
# 사전: ~/.ssh/coin-quant-key.pem 준비, EC2에 gemini CLI 설치 완료 가정
set -euo pipefail

EC2_HOST="ubuntu@3.37.118.119"
EC2_KEY="${EC2_KEY:-$HOME/.ssh/coin-quant-key.pem}"
REMOTE_DIR="/home/ubuntu/bbc_daily_report"

echo "[1/4] 코드 업로드 → $EC2_HOST:$REMOTE_DIR"
ssh -i "$EC2_KEY" "$EC2_HOST" "mkdir -p $REMOTE_DIR/reports"
scp -i "$EC2_KEY" \
    fetch.py summarize.py render.py scrape.py push.py main.py \
    requirements.txt deploy_ec2.sh \
    "$EC2_HOST:$REMOTE_DIR/"

echo "[2/4] venv + 의존성 설치"
ssh -i "$EC2_KEY" "$EC2_HOST" bash -lc "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
"

echo "[3/4] gemini CLI 동작 확인"
ssh -i "$EC2_KEY" "$EC2_HOST" "echo 'Say OK only' | gemini -p" || {
  echo "  ! gemini CLI 응답 실패 — \$PATH/login 확인 필요"; exit 1;
}

echo "[4/4] 스모크 테스트 (카테고리당 1건)"
ssh -i "$EC2_KEY" "$EC2_HOST" bash -lc "
  cd $REMOTE_DIR
  BBC_AI_BACKEND=gemini ./.venv/bin/python main.py --per 1 --no-push
"

echo
echo "✅ 배포 완료. cron 등록은 다음 명령:"
echo "  ssh -i $EC2_KEY $EC2_HOST"
echo "  crontab -e"
echo "  # 추가:"
echo "  0 23 * * * cd $REMOTE_DIR && BBC_AI_BACKEND=gemini ./.venv/bin/python main.py >> run.log 2>&1"
echo "  (UTC 23:00 = KST 08:00)"
