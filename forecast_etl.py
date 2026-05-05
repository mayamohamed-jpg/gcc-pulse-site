# forecast_etl.py
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

def prepare_features(df, brand, country):
    """Prepare features for time series forecasting"""
    brand_data = df[(df['Brand'] == brand) & (df['Country'] == country)].copy()
    brand_data = brand_data.sort_values(['Year', 'Q_Num'])
    
    if len(brand_data) < 4:
        return None
    
    features = []
    for i in range(len(brand_data)):
        row = brand_data.iloc[i]
        features.append({
            'year': row['Year'],
            'quarter': row['Q_Num'],
            'units': row['Units'],
            'quarter_sin': np.sin(2 * np.pi * row['Q_Num'] / 4),
            'quarter_cos': np.cos(2 * np.pi * row['Q_Num'] / 4),
            'time_index': i,
            'rolling_mean_2q': brand_data['Units'].rolling(2).mean().iloc[i] if i >= 1 else row['Units'],
            'rolling_mean_4q': brand_data['Units'].rolling(4).mean().iloc[i] if i >= 3 else row['Units'],
            'lag_1': brand_data['Units'].shift(1).iloc[i] if i >= 1 else row['Units'],
            'lag_2': brand_data['Units'].shift(2).iloc[i] if i >= 2 else row['Units'],
            'lag_4': brand_data['Units'].shift(4).iloc[i] if i >= 4 else row['Units'],
        })
    
    return pd.DataFrame(features)

def forecast_brand_country(df, brand, country, future_periods=3):
    """Forecast future units for a specific brand in a specific country"""
    features_df = prepare_features(df, brand, country)
    
    if features_df is None or len(features_df) < 4:
        return None
    
    feature_cols = ['quarter_sin', 'quarter_cos', 'time_index', 
                    'rolling_mean_2q', 'rolling_mean_4q', 'lag_1', 'lag_2', 'lag_4']
    
    X = features_df[feature_cols].ffill().bfill().values
    y = features_df['units'].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    models = {
        'rf': RandomForestRegressor(n_estimators=100, random_state=42),
        'gb': GradientBoostingRegressor(n_estimators=100, random_state=42),
        'lr': LinearRegression()
    }
    
    predictions = {}
    for name, model in models.items():
        model.fit(X_scaled, y)
        predictions[name] = model
    
    last_row = features_df.iloc[-1]
    last_quarter = int(last_row['quarter'])
    last_year = int(last_row['year'])
    last_time_index = int(last_row['time_index'])
    last_units = last_row['units']
    
    forecasts = []
    current_quarter = last_quarter
    current_year = last_year
    time_idx = last_time_index
    prev_units = last_units
    prev_prev_units = features_df['units'].iloc[-2] if len(features_df) >= 2 else last_units
    prev_4_units = features_df['units'].iloc[-4] if len(features_df) >= 4 else last_units
    
    rolling_2q = features_df['rolling_mean_2q'].dropna()
    rolling_4q = features_df['rolling_mean_4q'].dropna()
    last_rolling_2q = rolling_2q.iloc[-1] if len(rolling_2q) > 0 else last_units
    last_rolling_4q = rolling_4q.iloc[-1] if len(rolling_4q) > 0 else last_units
    
    for i in range(future_periods):
        current_quarter += 1
        if current_quarter > 4:
            current_quarter = 1
            current_year += 1
        
        future_features = np.array([[
            np.sin(2 * np.pi * current_quarter / 4),
            np.cos(2 * np.pi * current_quarter / 4),
            time_idx + i + 1,
            (last_units + prev_units) / 2,  # rolling mean 2q
            (last_units + prev_units + prev_prev_units + prev_4_units) / 4,  # rolling mean 4q
            last_units,  # lag 1
            prev_units,  # lag 2
            prev_4_units  # lag 4
        ]])
        
        future_scaled = scaler.transform(future_features)
        
        pred_values = []
        for model in predictions.values():
            pred_values.append(model.predict(future_scaled)[0])
        
        pred_units = max(0, int(np.mean(pred_values)))
        
        forecasts.append({
            'year': current_year,
            'quarter': f'Q{current_quarter}',
            'quarter_label': f'{current_year}Q{current_quarter}',
            'predicted_units': pred_units,
            'monthly_breakdown': [
                {'month': m, 'units': max(0, int(pred_units / 3 + np.random.randint(-int(pred_units*0.05), int(pred_units*0.05))))}
                for m in range(1, 4)
            ]
        })
        
        prev_4_units = prev_units
        prev_prev_units = prev_units
        prev_units = pred_units
        last_units = pred_units
    
    return forecasts

def calculate_forecast_growth(historical_units, forecast_units, period='qoq'):
    """Calculate QoQ or YoY growth for forecast"""
    if period == 'qoq':
        if historical_units > 0:
            return ((forecast_units - historical_units) / historical_units) * 100
        return 0
    else:  # yoy
        if historical_units > 0:
            return ((forecast_units - historical_units) / historical_units) * 100
        return 0

def run_forecast_pipeline():
    """Main forecast pipeline"""
    with open('gcc_dashboard.json', 'r') as f:
        data = json.load(f)
    
    brand_data = pd.DataFrame(data['brand_analysis'])
    
    quarter_cols = [col for col in brand_data.columns if col.startswith('Units_')]
    id_vars = ['Country', 'Brand']
    
    df_melted = brand_data[id_vars + quarter_cols].melt(
        id_vars=id_vars,
        value_vars=quarter_cols,
        var_name='Quarter',
        value_name='Units'
    )
    
    df_melted['Quarter'] = df_melted['Quarter'].str.replace('Units_', '')
    df_melted['Year'] = df_melted['Quarter'].str[:4].astype(int)
    df_melted['Q_Num'] = df_melted['Quarter'].str[5:].str.replace('Q', '').astype(int)
    
    countries = df_melted['Country'].unique()
    brands = df_melted['Brand'].unique()
    
    print(f"Forecasting for {len(countries)} countries and {len(brands)} brands...")
    
    forecast_results = {
        'brand_forecasts': {},
        'country_forecasts': {},
        'gcc_forecast': {},
        'summary': {}
    }
    
    for country in countries:
        country_forecasts = []
        for brand in brands:
            result = forecast_brand_country(df_melted, brand, country)
            if result:
                country_forecasts.append({
                    'brand': brand,
                    'forecasts': result
                })
        
        if country_forecasts:
            forecast_results['brand_forecasts'][country] = country_forecasts
    
    for country in countries:
        if country in forecast_results['brand_forecasts']:
            country_total = {}
            for brand_data in forecast_results['brand_forecasts'][country]:
                for fc in brand_data['forecasts']:
                    q = fc['quarter_label']
                    if q not in country_total:
                        country_total[q] = 0
                    country_total[q] += fc['predicted_units']
            
            country_quarterly = pd.DataFrame(data['country_overview'])
            country_row = country_quarterly[country_quarterly['Country'] == country]
            
            country_forecast_list = []
            for q, units in country_total.items():
                year = int(q[:4])
                q_num = int(q[5])
                
                # Find historical data for QoQ and YoY
                prev_q = f"{year}Q{q_num-1}" if q_num > 1 else f"{year-1}Q4"
                prev_y_q = f"{year-1}Q{q_num}"
                
                qoq = None
                yoy = None
                
                if prev_q in country_total:
                    qoq = calculate_forecast_growth(country_total.get(prev_q, 0), units)
                elif not country_row.empty and prev_q in country_row.columns:
                    qoq = calculate_forecast_growth(country_row[prev_q].values[0], units)
                
                if prev_y_q in country_total:
                    yoy = calculate_forecast_growth(country_total.get(prev_y_q, 0), units)
                elif not country_row.empty and prev_y_q in country_row.columns:
                    yoy = calculate_forecast_growth(country_row[prev_y_q].values[0], units)
                
                country_forecast_list.append({
                    'quarter': q,
                    'units': units,
                    'qoq_growth': round(qoq, 2) if qoq is not None else None,
                    'yoy_growth': round(yoy, 2) if yoy is not None else None,
                    'qoq_direction': '▲' if (qoq or 0) >= 0 else '▼',
                    'yoy_direction': '▲' if (yoy or 0) >= 0 else '▼'
                })
            
            forecast_results['country_forecasts'][country] = country_forecast_list
    
    gcc_total = {}
    for country_data in forecast_results['country_forecasts'].values():
        for fc in country_data:
            q = fc['quarter']
            if q not in gcc_total:
                gcc_total[q] = 0
            gcc_total[q] += fc['units']
    
    gcc_forecast_list = []
    for q, units in gcc_total.items():
        q_list = list(gcc_total.keys())
        idx = q_list.index(q)
        prev_q = q_list[idx-1] if idx > 0 else None
        prev_y_q = f"{int(q[:4])-1}Q{q[5]}" if f"{int(q[:4])-1}Q{q[5]}" in gcc_total else None
        
        qoq = calculate_forecast_growth(gcc_total.get(prev_q, 0), units) if prev_q else None
        yoy = calculate_forecast_growth(gcc_total.get(prev_y_q, 0), units) if prev_y_q else None
        
        gcc_forecast_list.append({
            'quarter': q,
            'units': units,
            'qoq_growth': round(qoq, 2) if qoq is not None else None,
            'yoy_growth': round(yoy, 2) if yoy is not None else None,
            'qoq_direction': '▲' if (qoq or 0) >= 0 else '▼',
            'yoy_direction': '▲' if (yoy or 0) >= 0 else '▼'
        })
    
    forecast_results['gcc_forecast'] = gcc_forecast_list
    
    total_forecasted_units = sum(gcc_total.values())
    avg_qoq = np.mean([f['qoq_growth'] for f in gcc_forecast_list if f['qoq_growth'] is not None])
    avg_yoy = np.mean([f['yoy_growth'] for f in gcc_forecast_list if f['yoy_growth'] is not None])
    
    forecast_results['summary'] = {
        'total_forecasted_units': total_forecasted_units,
        'avg_qoq_growth': round(avg_qoq, 2),
        'avg_yoy_growth': round(avg_yoy, 2),
        'forecast_periods': list(gcc_total.keys()),
        'model_accuracy': 'Ensemble (RF + GB + LR)',
        'generated_at': datetime.now().isoformat()
    }
    
    with open('forecast_data.json', 'w') as f:
        json.dump(forecast_results, f, indent=2, default=str)
    
    print(f"Forecast completed. Results saved to forecast_data.json")
    print(f"Total forecasted units: {total_forecasted_units:,}")
    print(f"Avg QoQ growth: {avg_qoq:.2f}%")
    print(f"Avg YoY growth: {avg_yoy:.2f}%")
    
    return forecast_results

if __name__ == "__main__":
    run_forecast_pipeline()