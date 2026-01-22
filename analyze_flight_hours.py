"""
Aviation Safety Data Analysis
Phân tích giờ bay tích lũy của phi hành đoàn
"""

import pandas as pd

# ========================================
# BƯỚC 1: HÀM CHUYỂN ĐỔI VÀ PHÂN LOẠI
# ========================================

def time_to_decimal(time_str):
    """Chuyển đổi định dạng HH:MM sang số thập phân."""
    if pd.isna(time_str) or time_str == '':
        return 0.0
    try:
        parts = str(time_str).strip().split(':')
        if len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return round(hours + minutes / 60, 2)
    except:
        return 0.0
    return 0.0

def classify_status(hours, limit=1000):
    """Phân loại trạng thái dựa trên giờ bay 12 tháng."""
    if hours > limit * 0.95:  # > 950 giờ
        return 'Critical'
    elif hours > limit * 0.85:  # > 850 giờ
        return 'Warning'
    else:
        return 'Normal'

# ========================================
# BƯỚC 2: ĐỌC VÀ LÀM SẠCH DỮ LIỆU
# ========================================

file_path = r'd:\Python\Json convert\RolCrTotReport.csv'

# Đọc file CSV, bỏ qua 5 dòng đầu (header metadata)
df_raw = pd.read_csv(file_path, skiprows=5, header=None, encoding='utf-8')

# Đặt tên cột
df_raw.columns = ['ID', 'Name', 'Seniority', '28Day_BlockTime', '12Month_BlockTime']

# Loại bỏ các dòng metadata cuối file (chỉ giữ dòng có ID là số)
df = df_raw[df_raw['ID'].apply(lambda x: str(x).strip().isdigit() if pd.notna(x) else False)].copy()

# Chuyển đổi ID sang số nguyên
df['ID'] = df['ID'].astype(int)

# ========================================
# BƯỚC 3: CHUYỂN ĐỔI ĐỊNH DẠNG GIỜ BAY
# ========================================

# Chuyển HH:MM sang Decimal
df['28Day_Decimal'] = df['28Day_BlockTime'].apply(time_to_decimal)
df['12Month_Decimal'] = df['12Month_BlockTime'].apply(time_to_decimal)

# Phân loại trạng thái cho 12 tháng
df['Status'] = df['12Month_Decimal'].apply(classify_status)

# ========================================
# BƯỚC 4: TẠO BÁO CÁO
# ========================================

# Top 20 theo 28 Days (giảm dần)
top20_28days = df.nlargest(20, '28Day_Decimal')[
    ['ID', 'Name', '28Day_BlockTime', '28Day_Decimal']
].reset_index(drop=True)
top20_28days.index = top20_28days.index + 1  # Đánh số từ 1

# Top 20 theo 12 Months (giảm dần)
top20_12months = df.nlargest(20, '12Month_Decimal')[
    ['ID', 'Name', '12Month_BlockTime', '12Month_Decimal', 'Status']
].reset_index(drop=True)
top20_12months.index = top20_12months.index + 1  # Đánh số từ 1

# Tính % so với giới hạn
top20_12months['Pct_Limit'] = (top20_12months['12Month_Decimal'] / 1000 * 100).round(1)

# ========================================
# BƯỚC 5: THỐNG KÊ TỔNG HỢP
# ========================================

status_counts = df['Status'].value_counts()
critical_list = df[df['Status'] == 'Critical'][['ID', 'Name', '12Month_Decimal']].sort_values(
    '12Month_Decimal', ascending=False
)
warning_list = df[df['Status'] == 'Warning'][['ID', 'Name', '12Month_Decimal']].sort_values(
    '12Month_Decimal', ascending=False
)

# ========================================
# BƯỚC 6: HIỂN THỊ KẾT QUẢ
# ========================================

print("=" * 80)
print("           BÁO CÁO PHÂN TÍCH GIỜ BAY PHI HÀNH ĐOÀN")
print("           (Rolling Crew Hours Totals Report)")
print("=" * 80)
print(f"\nNgày báo cáo: 15/01/2026")
print(f"Tổng số phi công: {len(df)} người\n")

print("-" * 80)
print("BẢNG 1: TOP 20 HIGH-INTENSITY CREW (ROLLING 28 DAYS)")
print("-" * 80)
print(f"{'Rank':<5} {'ID':<8} {'Name':<45} {'28Day(HH:MM)':<15} {'Decimal':<10}")
print("-" * 80)
for idx, row in top20_28days.iterrows():
    print(f"{idx:<5} {row['ID']:<8} {row['Name'][:44]:<45} {row['28Day_BlockTime']:<15} {row['28Day_Decimal']:<10.2f}")

print("\n" + "-" * 80)
print("BẢNG 2: TOP 20 HIGH-INTENSITY CREW (ROLLING 12 MONTHS)")
print("-" * 80)
print(f"{'Rank':<5} {'ID':<8} {'Name':<40} {'12Month(HH:MM)':<15} {'Decimal':<10} {'%Limit':<8} {'Status':<10}")
print("-" * 80)
for idx, row in top20_12months.iterrows():
    status_icon = "🔴" if row['Status'] == 'Critical' else ("🟡" if row['Status'] == 'Warning' else "🟢")
    print(f"{idx:<5} {row['ID']:<8} {row['Name'][:39]:<40} {row['12Month_BlockTime']:<15} {row['12Month_Decimal']:<10.2f} {row['Pct_Limit']:<8.1f} {status_icon} {row['Status']:<10}")

print("\n" + "=" * 80)
print("THỐNG KÊ PHÂN LOẠI SAFETY COMPLIANCE")
print("=" * 80)
print(f"🔴 Critical (>950h / >95%): {status_counts.get('Critical', 0):>5} người ({status_counts.get('Critical', 0)/len(df)*100:.1f}%)")
print(f"🟡 Warning  (>850h / >85%): {status_counts.get('Warning', 0):>5} người ({status_counts.get('Warning', 0)/len(df)*100:.1f}%)")
print(f"🟢 Normal   (≤850h):        {status_counts.get('Normal', 0):>5} người ({status_counts.get('Normal', 0)/len(df)*100:.1f}%)")
print(f"📊 Tổng cộng:               {len(df):>5} người")

print("\n" + "=" * 80)
print("DANH SÁCH PHI CÔNG CRITICAL (CẦN LƯU Ý ĐẶC BIỆT)")
print("=" * 80)
print(f"{'No':<4} {'ID':<8} {'Name':<45} {'12Month (h)':<12} {'Còn lại (h)':<12}")
print("-" * 80)
for i, (idx, row) in enumerate(critical_list.iterrows(), 1):
    remaining = 1000 - row['12Month_Decimal']
    print(f"{i:<4} {row['ID']:<8} {row['Name'][:44]:<45} {row['12Month_Decimal']:<12.2f} {remaining:<12.2f}")

print("\n" + "=" * 80)
print("KẾT THÚC BÁO CÁO")
print("=" * 80)
