# Crew Management Dashboard

Dashboard quản lý phi hành đoàn với các tính năng:
- 📊 Executive Summary (Tổng quan điều hành)
- ⚠️ Safety & Compliance (An toàn & Tuân thủ)
- 🔄 Operational Agility (Linh hoạt vận hành)
- 📈 Rolling block hours tracking (28-day / 365-day limits)
- 👥 Crew schedule monitoring (Standby, Sick-call, Fatigue)

## Chạy local

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy server
python api_server.py
```

Mở browser tại: http://localhost:5000

## Deploy lên Render.com

### Bước 1: Push code lên GitHub
```bash
git init
git add .
git commit -m "Initial commit - Crew Dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/crew-dashboard.git
git push -u origin main
```

### Bước 2: Deploy trên Render
1. Đăng ký tài khoản tại https://render.com
2. Click **New** → **Web Service**
3. Connect GitHub repo của bạn
4. Render sẽ tự động detect `render.yaml` và cấu hình
5. Click **Deploy**

Website sẽ có địa chỉ: `https://crew-dashboard.onrender.com`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Lấy tất cả dữ liệu dashboard |
| GET | `/api/summary` | Lấy KPIs tóm tắt |
| GET | `/api/aircraft` | Danh sách tàu bay |
| GET | `/api/crew` | Thống kê phi hành đoàn |
| GET | `/api/utilization` | Dữ liệu aircraft utilization |
| POST | `/api/upload/dayrep` | Upload DayRepReport CSV |
| POST | `/api/upload/sacutil` | Upload SacutilReport CSV |
| POST | `/api/upload/rolcrtot` | Upload RolCrTotReport CSV |
| POST | `/api/upload/crew_schedule` | Upload Crew Schedule CSV |

## Upload CSV Files

Dashboard hỗ trợ upload các file CSV sau:
- **DayRepReport**: Báo cáo chuyến bay hàng ngày
- **SacutilReport**: Báo cáo utilization tàu bay
- **RolCrTotReport**: Rolling block hours (28-day/365-day)
- **Crew Schedule**: Lịch trình SBY, CSL, SL, OSBY

## License

VietJet Air - Internal Use Only
