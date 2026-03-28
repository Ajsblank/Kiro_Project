# Kiro Tournament Project

AWS 기반 실시간 토너먼트 + 치토 배틀 게임

## 구성
- `tournament/index.html` - 토너먼트 메인 (S3 정적 호스팅)
- `tournament/chito.html` - 치토 배틀 게임
- `tournament/lambda_function.py` - API Lambda 함수

## 배포
- Frontend: S3 (`ajuuniv-10-s3-kiro`)
- Backend: API Gateway + Lambda (`tournament-api`)
- DB: RDS MySQL (`db_10`)

## 접속
http://ajuuniv-10-s3-kiro.s3-website-us-east-1.amazonaws.com
