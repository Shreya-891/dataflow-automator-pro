"""
Generate sample data files for testing DataFlow Automator Pro.
"""

import os
import json
import pandas as pd
import numpy as np

sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_files")
os.makedirs(sample_dir, exist_ok=True)

# 1. Messy CSV
df_sales = pd.DataFrame({
    'Transaction ID ': [f'TXN-{1000+i}' for i in range(25)],
    'Customer Name ': ['John Doe', 'Jane Smith', 'Acme Corp', 'Global Tech', 'John Doe'] * 5,
    'Region': ['North', 'South', 'East', 'West', 'North'] * 5,
    'Product Category ': ['Software', 'Cloud Services', 'Hardware', 'Consulting', 'Software'] * 5,
    'Revenue USD': ['$1,250.00', '$4,500.50', '$850.00', '$12,000.00', '$1,250.00'] * 5,
    'Units Sold': [5, 12, np.nan, 2, 5] * 5,
    'Discount Rate': ['10%', '5%', '0%', '15%', '10%'] * 5
})
df_sales.to_csv(os.path.join(sample_dir, 'sales_q3_raw.csv'), index=False)

# 2. Sample Excel
df_budget = pd.DataFrame({
    'Department': ['Engineering', 'Marketing', 'Sales', 'Human Resources', 'Executive'],
    'Allocated Budget': [450000, 180000, 220000, 95000, 150000],
    'Spent To Date': [390000, 165000, 195000, 82000, 140000],
    'Remaining Balance': [60000, 15000, 25000, 13000, 10000]
})
df_budget.to_excel(os.path.join(sample_dir, 'annual_budget_forecast.xlsx'), index=False)

# 3. Documents and Images
with open(os.path.join(sample_dir, 'project_spec_draft.docx'), 'w') as f:
    f.write('Specification document content placeholder.')

with open(os.path.join(sample_dir, 'monthly_invoice_oct2026.pdf'), 'w') as f:
    f.write('%PDF-1.4 Mock PDF stream content.')

with open(os.path.join(sample_dir, 'api_config.json'), 'w') as f:
    json.dump({"service": "DataFlow", "version": "1.0.0", "active": True}, f, indent=2)

# Duplicate pair for testing SHA-256 hash detection
img_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
with open(os.path.join(sample_dir, 'architecture_diagram.png'), 'wb') as f:
    f.write(img_bytes)

with open(os.path.join(sample_dir, 'architecture_diagram_copy.png'), 'wb') as f:
    f.write(img_bytes)

print(f"Generated sample files in {sample_dir}")
