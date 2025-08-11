import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Load data function
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    
    # Convert date columns to datetime
    date_cols = ['Picked on', 'First attempted on', 'Delivered on']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format='%m-%d-%Y %H:%M', errors='coerce')
    
    return df

# Filter data for specific month
def filter_month_data(df, month):
    df_month = df[df['Picked on'].dt.month == month]
    return df_month

# Process data for same day performance
def process_same_day(df_month):
    same_day_data = []
    
    # Get unique dates in the month
    dates_in_month = pd.date_range(
        start=df_month['Picked on'].min().replace(day=1),
        end=df_month['Picked on'].max() + pd.Timedelta(days=1),
        freq='D'
    )
    
    # Define special customers
    special_customers = [
        'WESTSIDE UNIT OF TRENT LIMITED', 
        'TATA CLiQ', 
        'ZISHTA TRADITIONS PRIVATE LIMITED', 
        'Heads Up for Tails HUFT'
    ]
    
    for date in dates_in_month:
        date_str = date.strftime('%Y-%m-%d')
        
        # Filter orders picked on this date
        picked_orders = df_month[df_month['Picked on'].dt.date == date.date()]
        
        # Split into special and regular customers
        regular_orders = picked_orders[~picked_orders['Customer'].isin(special_customers)]
        special_orders = picked_orders[picked_orders['Customer'].isin(special_customers)]
        
        # For special customers, only count if picked before 3PM
        valid_special_orders = special_orders[special_orders['Picked on'].dt.hour < 15]
        
        # For regular customers, count all regardless of time
        valid_regular_orders = regular_orders
        
        # Combine valid orders
        valid_orders = pd.concat([valid_regular_orders, valid_special_orders])
        
        same_day_orders = len(valid_orders)
        
        # Attempted orders (first attempt on same day)
        attempted = len(valid_orders[valid_orders['First attempted on'].dt.date == date.date()])
        
        # Delivered orders (delivered on same day)
        delivered = len(valid_orders[valid_orders['Delivered on'].dt.date == date.date()])
        
        # Calculate percentages
        attempted_pct = (attempted / same_day_orders * 100) if same_day_orders > 0 else 0
        delivered_pct = (delivered / same_day_orders * 100) if same_day_orders > 0 else 0
        
        same_day_data.append({
            'Date': date_str,
            'Same day Orders': same_day_orders,
            'Attempted': attempted,
            'Attempted %': round(attempted_pct, 2),
            'Delivered': delivered,
            'Delivered %': round(delivered_pct, 2)
        })
    
    return pd.DataFrame(same_day_data)

# Process data for next day performance (special customers after 3PM only)
def process_next_day(df_month):
    next_day_data = []
    
    # Get unique dates in the month
    dates_in_month = pd.date_range(
        start=df_month['Picked on'].min().replace(day=1),
        end=df_month['Picked on'].max() + pd.Timedelta(days=1),
        freq='D'
    )
    
    # Define special customers
    special_customers = [
        'WESTSIDE UNIT OF TRENT LIMITED', 
        'TATA CLiQ', 
        'ZISHTA TRADITIONS PRIVATE LIMITED', 
        'Heads Up for Tails HUFT'
    ]
    
    for date in dates_in_month:
        date_str = date.strftime('%Y-%m-%d')
        previous_date = date - pd.Timedelta(days=1)
        
        # Filter ONLY special customer orders picked after 3PM the previous day
        special_orders = df_month[
            (df_month['Customer'].isin(special_customers)) &
            (df_month['Picked on'].dt.date == previous_date.date()) &
            (df_month['Picked on'].dt.hour >= 15)
        ]
        
        # Total next day orders (only special orders picked previous day after 3PM)
        next_day_orders_count = len(special_orders)
        
        # Attempted logic:
        # 1. First attempted on previous day (same day as picked)
        attempted_previous_day = len(special_orders[
            (special_orders['First attempted on'].dt.date == previous_date.date())
        ])
        
        # 2. First attempted on current date (next day)
        attempted_current_day = len(special_orders[
            (special_orders['First attempted on'].dt.date == date.date())
        ])
        
        total_attempted = attempted_previous_day + attempted_current_day
        
        # Delivered logic:
        # 1. Delivered on previous day (same day as picked)
        delivered_previous_day = len(special_orders[
            (special_orders['Delivered on'].dt.date == previous_date.date())
        ])
        
        # 2. Delivered on current date (next day)
        delivered_current_day = len(special_orders[
            (special_orders['Delivered on'].dt.date == date.date())
        ])
        
        total_delivered = delivered_previous_day + delivered_current_day
        
        # Calculate percentages
        attempted_pct = (total_attempted / next_day_orders_count * 100) if next_day_orders_count > 0 else 0
        delivered_pct = (total_delivered / next_day_orders_count * 100) if next_day_orders_count > 0 else 0
        
        next_day_data.append({
            'Date': date_str,
            'Next day Orders': next_day_orders_count,
            'Attempted': total_attempted,
            'Attempted %': round(attempted_pct, 2),
            'Delivered': total_delivered,
            'Delivered %': round(delivered_pct, 2),
            'Attempted Previous Day': attempted_previous_day,
            'Attempted Current Day': attempted_current_day,
            'Delivered Previous Day': delivered_previous_day,
            'Delivered Current Day': delivered_current_day
        })
    
    return pd.DataFrame(next_day_data)

# Apply full cell color formatting
def color_cells(val):
    if isinstance(val, (int, float)):
        if val >= 95:
            return 'background-color: #4CAF50; color: white'  # Green
        elif val >= 85:
            return 'background-color: #FFEB3B; color: black'  # Yellow
        else:
            return 'background-color: #F44336; color: white'  # Red
    return ''

# Format the entire dataframe with color
def format_dataframe(df, percentage_cols):
    # Apply to percentage columns
    styled_df = df.style.applymap(color_cells, subset=percentage_cols)
    
    # Format numeric columns
    styled_df = styled_df.format({
        'Same day Orders': '{:.0f}',
        'Attempted': '{:.0f}',
        'Attempted %': '{:.1f}%',
        'Delivered': '{:.0f}',
        'Delivered %': '{:.1f}%',
        'Next day Orders': '{:.0f}',
    })
    
    # Set table properties
    styled_df = styled_df.set_properties(**{
        'text-align': 'center',
        'border': '1px solid black'
    })
    
    return styled_df

# Plot comparison graphs
def plot_comparison(same_day_df, next_day_df, month_name):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Attempted % comparison
    ax1.plot(same_day_df['Date'], same_day_df['Attempted %'], label='Same Day', marker='o')
    ax1.plot(next_day_df['Date'], next_day_df['Attempted %'], label='Next Day', marker='o')
    ax1.set_title(f'{month_name} - Attempted % Comparison')
    ax1.set_ylabel('Percentage')
    ax1.legend()
    ax1.grid(True)
    ax1.tick_params(axis='x', rotation=45)
    
    # Delivered % comparison
    ax2.plot(same_day_df['Date'], same_day_df['Delivered %'], label='Same Day', marker='o')
    ax2.plot(next_day_df['Date'], next_day_df['Delivered %'], label='Next Day', marker='o')
    ax2.set_title(f'{month_name} - Delivered % Comparison')
    ax2.set_ylabel('Percentage')
    ax2.legend()
    ax2.grid(True)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    st.pyplot(fig)

# Main Streamlit app
def main():
    st.title('Delivery Performance Analysis')
    
    uploaded_file = st.file_uploader("Upload your delivery data CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        # Create tabs for each month
        tab_names = ["March", "April", "May", "June", "July", "August"]
        tabs = st.tabs(tab_names)
        
        months = {
            'March': 3,
            'April': 4,
            'May': 5,
            'June': 6,
            'July': 7,
            'August': 8
        }
        
        for i, (month_name, month_num) in enumerate(months.items()):
            with tabs[i]:  # Use the index to access the correct tab
                st.header(month_name)
                
                # Filter data for the month
                month_data = filter_month_data(df, month_num)
                
                if not month_data.empty:
                    # Process data for same day and next day performance
                    same_day_df = process_same_day(month_data)
                    next_day_df = process_next_day(month_data)
                    
                    # Display Same Day table with full color formatting
                    st.subheader("Same Day Performance")
                    styled_same_day = format_dataframe(
                        same_day_df[['Date', 'Same day Orders', 'Attempted', 'Attempted %', 'Delivered', 'Delivered %']],
                        percentage_cols=['Attempted %', 'Delivered %']
                    )
                    st.dataframe(styled_same_day, use_container_width=True)
                    
                    # Display Next Day table with full color formatting
                    st.subheader("Next Day Performance (Special Customers after 3PM only)")
                    styled_next_day = format_dataframe(
                        next_day_df[['Date', 'Next day Orders', 'Attempted', 'Attempted %', 'Delivered', 'Delivered %']],
                        percentage_cols=['Attempted %', 'Delivered %']
                    )
                    st.dataframe(styled_next_day, use_container_width=True)
                    
                    # Show additional details in expander
                    with st.expander("Show Next Day Detailed Breakdown"):
                        st.write("""
                        - **Next Day Orders**: Special customer orders picked after 3PM previous day
                        - **Attempted Previous Day**: First attempt on same day as pickup (after 3PM)
                        - **Attempted Current Day**: First attempt on next day after pickup
                        - **Delivered Previous Day**: Delivered on same day as pickup (after 3PM)
                        - **Delivered Current Day**: Delivered on next day after pickup
                        """)
                        st.dataframe(next_day_df[['Date', 'Next day Orders', 
                                              'Attempted Previous Day', 'Attempted Current Day',
                                              'Delivered Previous Day', 'Delivered Current Day']])
                    
                    # Show comparison graphs
                    st.subheader("Performance Comparison")
                    plot_comparison(same_day_df, next_day_df, month_name)
                else:
                    st.warning(f"No data available for {month_name}")

if __name__ == "__main__":
    main()
