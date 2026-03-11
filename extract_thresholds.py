import pandas as pd
import json

prod = pd.read_excel('_h_batch_production_data.xlsx')

xl = pd.ExcelFile('_h_batch_process_data.xlsx')
power_stats = []
for sheet in xl.sheet_names:
    if not sheet.startswith("Batch_T"): 
        continue
    try:
        df = xl.parse(sheet)
        batch_id = df['Batch_ID'].iloc[0]
        avg_power = df['Power_Consumption_kW'].mean()
        peak_power = df['Power_Consumption_kW'].max()
        power_stats.append({'Batch_ID': batch_id, 'avg_power': avg_power, 'peak_power': peak_power})
    except Exception as e:
        print(f"Skipping {sheet}: {e}")

power_df = pd.DataFrame(power_stats)
merged = prod.merge(power_df, on='Batch_ID')

golden = merged[merged['Dissolution_Rate'] >= 90]
bad = merged[merged['Dissolution_Rate'] < 90]

thresholds = {
    'golden_avg_power_max': float(golden['avg_power'].max()),
    'golden_peak_power_max': float(golden['peak_power'].max()),
    'golden_avg_power_p75': float(golden['avg_power'].quantile(0.75)),
    'golden_peak_power_p75': float(golden['peak_power'].quantile(0.75)),
    'bad_avg_power_mean': float(bad['avg_power'].mean()),
    'bad_peak_power_mean': float(bad['peak_power'].mean()),
}

print("-" * 50)
print(merged[['Batch_ID', 'Dissolution_Rate', 'avg_power', 'peak_power']].sort_values(by='Dissolution_Rate', ascending=False).head(10).to_string())
print("-" * 50)
print(merged[['Batch_ID', 'Dissolution_Rate', 'avg_power', 'peak_power']].sort_values(by='Dissolution_Rate', ascending=False).tail(10).to_string())
print("-" * 50)

print(json.dumps(thresholds, indent=2))
