import app
from datetime import datetime, timedelta

token = app._get_sp_token()
auth = {'Authorization': f'Bearer {token}'}
site = app._get_site_id(auth)
base_url = app._get_base_url(site)

url = f'{base_url}/workbook/worksheets/{app.SP_SHEET_GASTOS}/usedRange'
r = app.req_lib.get(url, headers=auth).json()
values = r.get('values', [])
address = r.get('address')

excel_epoch = datetime(1899, 12, 30)

fixed_values = []
for i, row in enumerate(values):
    if i == 0:
        fixed_values.append(row)
        continue
    
    new_row = list(row)
    changed = False
    
    # Process fecha_reg (index 0)
    raw_reg = row[0]
    if isinstance(raw_reg, (int, float)):
        dt = excel_epoch + timedelta(days=float(raw_reg))
        # Format as DD/MM/YYYY so Excel US either flips it (if ambiguous) or stores as string (if unambiguous)
        new_row[0] = dt.strftime("%d/%m/%Y %H:%M")
        changed = True
    elif isinstance(raw_reg, str) and raw_reg:
        try:
            # Try to parse M/D/Y (in case it was stringified US format)
            dt = datetime.strptime(raw_reg, "%m/%d/%Y %H:%M")
            new_row[0] = dt.strftime("%d/%m/%Y %H:%M")
            changed = True
        except ValueError:
            try:
                # Already DD/MM/YYYY ?
                dt = datetime.strptime(raw_reg, "%d/%m/%Y %H:%M")
                # Leave it alone
            except ValueError:
                pass

    # Process fecha (index 2)
    raw_fecha = row[2]
    if isinstance(raw_fecha, (int, float)):
        dt = excel_epoch + timedelta(days=float(raw_fecha))
        new_row[2] = dt.strftime("%d/%m/%Y")
        changed = True
    elif isinstance(raw_fecha, str) and raw_fecha:
        try:
            dt = datetime.strptime(raw_fecha, "%m/%d/%Y")
            new_row[2] = dt.strftime("%d/%m/%Y")
            changed = True
        except ValueError:
            pass

    fixed_values.append(new_row)

range_only = address.split('!')[-1]
update_url = f'{base_url}/workbook/worksheets/{app.SP_SHEET_GASTOS}/range(address=\'{range_only}\')'
body = {"values": fixed_values}
res = app.req_lib.patch(update_url, headers=auth, json=body)
print(res.status_code, res.text)
