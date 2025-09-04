## Giới thiệu
Repo này chứa pipeline xử lý và phân tích dữ liệu chứng khoán.  
Quy trình chạy gồm 3 bước chính, thực hiện tuần tự từ **B1 → B2 → B3_4**.  
Mỗi bước sẽ sinh ra dữ liệu trung gian được sử dụng cho bước tiếp theo.  

- **Bước 1**: Tạo ra file `all_stock_data.csv`.  
- **Bước 2**: Import dữ liệu từ `all_stock_data.csv`, xử lý → sinh ra `full_data.csv`.  
- **Bước 3-4**: Import dữ liệu từ `full_data.csv` để xây dựng chiến lược.  

---

## Yêu cầu môi trường
- Python >= 3.12  
- Các thư viện cần thiết đã được liệt kê trong `requirements.txt`.  

Cài đặt nhanh:  
```bash
pip install -r requirements.txt
