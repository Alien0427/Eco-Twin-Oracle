import pandas as pd

# Load your actual dataset
df = pd.read_excel("_h_batch_process_data.xlsx") 

# Group by the CORRECT Batch_ID and find the average power
avg_power = df.groupby('Batch_ID')['Power_Consumption_kW'].mean().sort_values()

print("🏆 THE MOST EFFICIENT BATCHES (Run the top one in Streamlit!):")
print(avg_power.head(3))