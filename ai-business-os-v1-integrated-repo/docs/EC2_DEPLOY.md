# EC2 배포 순서

Windows PC에서 ZIP 다운로드 후 압축 해제.

PowerShell에서 EC2로 전송:

```powershell
scp -i ".\ai-business-os-key (1).pem" -r ".\ai-business-os-v1-integrated-repo" ubuntu@<EC2-DNS>:~/
```

EC2 접속 후:

```bash
cd ~/ai-business-os-v1-integrated-repo
cp .env.example .env
nano .env
```

최소한 다음 값을 변경:
- POSTGRES_PASSWORD
- DATABASE_URL의 비밀번호
- SECRET_KEY

그 다음:

```bash
chmod +x scripts/*.sh
./scripts/ec2_first_deploy.sh
```

외부 브라우저 확인 전에는 AWS Security Group에서 8000 포트를 무작정 전체 공개하지 않는 것을 권장합니다.
초기 검증은 SSH 터널 또는 제한된 IP 규칙을 사용하세요.
