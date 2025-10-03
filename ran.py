import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io

# Load data function
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    
    # Convert date columns to datetime
    date_cols = ['Picked on', 'First attempted on', 'Delivered on']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format='%m-%d-%Y %H:%M', errors='coerce')
    
    return df

# Find hub column name
def find_hub_column(df):
    hub_column_candidates = ['Delivery hub', 'Hub', 'Delivery Hub', 'Delivery_hub', 'delivery_hub', 'delivery hub']
    for col in hub_column_candidates:
        if col in df.columns:
            return col
    return None

# Filter data for specific month
def filter_month_data(df, month):
    df_month = df[df['Picked on'].dt.month == month]
    return df_month

# Process data for same day performance
def process_same_day(df_month, hub_filter="All", hub_column=None):
    same_day_data = []
    
    # Apply hub filter if specified and column exists
    if hub_filter != "All" and hub_column and hub_column in df_month.columns:
        df_month = df_month[df_month[hub_column] == hub_filter]
    
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
        
        # Skip if no orders
        if len(picked_orders) == 0:
            continue
            
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
        
        # Hub information
        if hub_filter != "All" and hub_column and hub_column in df_month.columns:
            hub = hub_filter
        else:
            hub = "All Hubs"
        
        same_day_data.append({
            'Date': date_str,
            'Hub': hub,
            'Same day Orders': same_day_orders,
            'Attempted': attempted,
            'Attempted %': round(attempted_pct, 2),
            'Delivered': delivered,
            'Delivered %': round(delivered_pct, 2)
        })
    
    return pd.DataFrame(same_day_data)

# Process data for next day performance (special customers after 3PM only)
def process_next_day(df_month, df_full, month_num, hub_filter="All", hub_column=None):
    next_day_data = []
    
    # Apply hub filter if specified and column exists
    if hub_filter != "All" and hub_column and hub_column in df_month.columns:
        df_month = df_month[df_month[hub_column] == hub_filter]
    
    # Get the first and last dates of the current month's data
    min_date = df_month['Picked on'].min()
    max_date = df_month['Picked on'].max()
    
    # Create date range for the entire month (not just days with data)
    dates_in_month = pd.date_range(
        start=datetime(min_date.year, month_num, 1),
        end=datetime(min_date.year, month_num, 1) + pd.offsets.MonthEnd(1),
        freq='D'
    )
    
    # Define special customers
    special_customers = [
        'WESTSIDE UNIT OF TRENT LIMITED', 
        'TATA CLiQ', 
        'ZISHTA TRADITIONS PRIVATE LIMITED', 
        'Ugaoo',
        'Heads Up for Tails HUFT'
    ]
    
    # Get previous month number and year
    prev_month = month_num - 1 if month_num > 1 else 12
    prev_year = min_date.year if month_num > 1 else min_date.year - 1
    
    for date in dates_in_month:
        date_str = date.strftime('%Y-%m-%d')
        previous_date = date - pd.Timedelta(days=1)
        
        # Determine which dataframe to use for the previous day's data
        if previous_date.month == month_num:
            # Previous day is in same month - use current month's data
            prev_day_df = df_month
        else:
            # Previous day is in previous month - use previous month's data from full dataframe
            prev_day_df = df_full[
                (df_full['Picked on'].dt.month == prev_month) & 
                (df_full['Picked on'].dt.year == prev_year)
            ]
            
            # Apply hub filter if specified and column exists
            if hub_filter != "All" and hub_column and hub_column in prev_day_df.columns:
                prev_day_df = prev_day_df[prev_day_df[hub_column] == hub_filter]
        
        # Filter ONLY special customer orders picked after 3PM the previous day
        special_orders = prev_day_df[
            (prev_day_df['Customer'].isin(special_customers)) &
            (prev_day_df['Picked on'].dt.date == previous_date.date()) &
            (prev_day_df['Picked on'].dt.hour >= 15)
        ]
        
        # Skip if no orders
        if len(special_orders) == 0:
            continue
        
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
        
        # Hub information
        if hub_filter != "All" and hub_column and hub_column in df_month.columns:
            hub = hub_filter
        else:
            hub = "All Hubs"
        
        next_day_data.append({
            'Date': date_str,
            'Hub': hub,
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

# Process hub-wise performance for all hubs
def process_all_hubs_performance(df_month, df_full, month_num, hub_column):
    if not hub_column or hub_column not in df_month.columns:
        return pd.DataFrame(), pd.DataFrame()
        
    hubs = df_month[hub_column].unique()
    all_same_day_data = []
    all_next_day_data = []
    
    for hub in hubs:
        # Process same day performance for this hub
        same_day_hub = process_same_day(df_month, hub, hub_column)
        if not same_day_hub.empty:
            all_same_day_data.append(same_day_hub)
        
        # Process next day performance for this hub
        next_day_hub = process_next_day(df_month, df_full, month_num, hub, hub_column)
        if not next_day_hub.empty:
            all_next_day_data.append(next_day_hub)
    
    # Combine all hub data
    same_day_all_hubs = pd.concat(all_same_day_data, ignore_index=True) if all_same_day_data else pd.DataFrame()
    next_day_all_hubs = pd.concat(all_next_day_data, ignore_index=True) if all_next_day_data else pd.DataFrame()
    
    return same_day_all_hubs, next_day_all_hubs

# Process hub-wise performance summary
def process_hub_performance(df_month, hub_column):
    if not hub_column or hub_column not in df_month.columns:
        return pd.DataFrame()
        
    hubs = df_month[hub_column].unique()
    hub_data = []
    
    for hub in hubs:
        # Same day performance for this hub
        same_day_hub = process_same_day(df_month, hub, hub_column)
        
        if not same_day_hub.empty:
            hub_attempted_avg = same_day_hub['Attempted %'].mean()
            hub_delivered_avg = same_day_hub['Delivered %'].mean()
            
            hub_data.append({
                'Hub': hub,
                'Avg Attempted %': round(hub_attempted_avg, 2),
                'Avg Delivered %': round(hub_delivered_avg, 2),
                'Total Orders': same_day_hub['Same day Orders'].sum()
            })
    
    return pd.DataFrame(hub_data)

# Process customer-wise performance
def process_customer_performance(df_month):
    customer_data = []
    
    # Group by customer and calculate performance metrics
    for customer, group in df_month.groupby('Customer'):
        total_orders = len(group)
        
        # Calculate same day attempted and delivered
        same_day_attempted = len(group[group['First attempted on'].dt.date == group['Picked on'].dt.date])
        same_day_delivered = len(group[group['Delivered on'].dt.date == group['Picked on'].dt.date])
        
        # Calculate percentages
        attempted_pct = (same_day_attempted / total_orders * 100) if total_orders > 0 else 0
        delivered_pct = (same_day_delivered / total_orders * 100) if total_orders > 0 else 0
        
        customer_data.append({
            'Customer': customer,
            'Total Orders': total_orders,
            'Same Day Attempted': same_day_attempted,
            'Attempted %': round(attempted_pct, 2),
            'Same Day Delivered': same_day_delivered,
            'Delivered %': round(delivered_pct, 2)
        })
    
    return pd.DataFrame(customer_data)

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
    for col in df.columns:
        if '%' in col:
            styled_df = styled_df.format({col: '{:.1f}%'})
        elif 'Orders' in col or 'Attempted' in col or 'Delivered' in col:
            styled_df = styled_df.format({col: '{:.0f}'})
    
    # Set table properties
    styled_df = styled_df.set_properties(**{
        'text-align': 'center',
        'border': '1px solid black'
    })
    
    return styled_df

# Plot comparison graphs
def plot_comparison(same_day_df, next_day_df, month_name, hub_name):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Attempted % comparison
    ax1.plot(same_day_df['Date'], same_day_df['Attempted %'], label='Same Day', marker='o')
    if not next_day_df.empty:
        ax1.plot(next_day_df['Date'], next_day_df['Attempted %'], label='Next Day', marker='o')
    ax1.set_title(f'{month_name} - {hub_name} - Attempted % Comparison')
    ax1.set_ylabel('Percentage')
    ax1.legend()
    ax1.grid(True)
    ax1.tick_params(axis='x', rotation=45)
    
    # Delivered % comparison
    ax2.plot(same_day_df['Date'], same_day_df['Delivered %'], label='Same Day', marker='o')
    if not next_day_df.empty:
        ax2.plot(next_day_df['Date'], next_day_df['Delivered %'], label='Next Day', marker='o')
    ax2.set_title(f'{month_name} - {hub_name} - Delivered % Comparison')
    ax2.set_ylabel('Percentage')
    ax2.legend()
    ax2.grid(True)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    st.pyplot(fig)

# Plot hub performance
def plot_hub_performance(hub_df, month_name):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Sort by performance
    hub_df_sorted = hub_df.sort_values('Avg Attempted %', ascending=False)
    
    # Attempted % by hub
    ax1.bar(hub_df_sorted['Hub'], hub_df_sorted['Avg Attempted %'])
    ax1.set_title(f'{month_name} - Avg Attempted % by Hub')
    ax1.set_ylabel('Percentage')
    ax1.tick_params(axis='x', rotation=45)
    
    # Delivered % by hub
    hub_df_sorted = hub_df.sort_values('Avg Delivered %', ascending=False)
    ax2.bar(hub_df_sorted['Hub'], hub_df_sorted['Avg Delivered %'])
    ax2.set_title(f'{month_name} - Avg Delivered % by Hub')
    ax2.set_ylabel('Percentage')
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    st.pyplot(fig)

# Plot customer performance
def plot_customer_performance(customer_df, month_name):
    # Filter to top 10 customers by order volume
    top_customers = customer_df.nlargest(10, 'Total Orders')
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Attempted % by customer
    ax1.barh(top_customers['Customer'], top_customers['Attempted %'])
    ax1.set_title(f'{month_name} - Attempted % by Customer (Top 10)')
    ax1.set_xlabel('Percentage')
    
    # Delivered % by customer
    ax2.barh(top_customers['Customer'], top_customers['Delivered %'])
    ax2.set_title(f'{month_name} - Delivered % by Customer (Top 10)')
    ax2.set_xlabel('Percentage')
    
    plt.tight_layout()
    st.pyplot(fig)

# Convert DataFrame to CSV for download
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Main Streamlit app
def main():
    st.title('Delivery Performance Analysis')
    
    uploaded_file = st.file_uploader("Upload your delivery data CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        # Find hub column name
        hub_column = find_hub_column(df)
        has_hub_column = hub_column is not None
        
        # Get unique hubs for filtering if column exists
        if has_hub_column:
            all_hubs = ["All"] + list(df[hub_column].unique())
            st.write(f"Detected hub column: '{hub_column}'")
        else:
            all_hubs = ["All"]
            st.warning("No hub column found in the data. Showing overall performance only.")
            # Show available columns to help identify the hub column
            st.write("Available columns in your CSV:")
            st.write(list(df.columns))
        
        # Create tabs for July, August, September only
        tab_names = ["July", "August", "September"]
        tabs = st.tabs(tab_names)
        
        months = {
            'July': 7,
            'August': 8,
            'September': 9
        }
        
        for i, (month_name, month_num) in enumerate(months.items()):
            with tabs[i]:  # Use the index to access the correct tab
                st.header(month_name)
                
                # Hub selection only if hub column exists
                if has_hub_column:
                    selected_hub = st.selectbox(
                        "Select Delivery Hub", 
                        all_hubs,
                        key=f"hub_select_{month_name}"
                    )
                else:
                    selected_hub = "All"
                
                # Filter data for the month
                month_data = filter_month_data(df, month_num)
                
                if not month_data.empty:
                    # Process data for same day and next day performance
                    same_day_df = process_same_day(month_data, selected_hub, hub_column)
                    next_day_df = process_next_day(month_data, df, month_num, selected_hub, hub_column)
                    
                    # Process hub-wise data for CSV export
                    if has_hub_column:
                        same_day_all_hubs, next_day_all_hubs = process_all_hubs_performance(month_data, df, month_num, hub_column)
                        
                        # Add download buttons for hub-wise data
                        col1, col2 = st.columns(2)
                        with col1:
                            if not same_day_all_hubs.empty:
                                csv_same_day = convert_df_to_csv(same_day_all_hubs)
                                st.download_button(
                                    label="Download Hub-wise Same Day Data (CSV)",
                                    data=csv_same_day,
                                    file_name=f"{month_name}_same_day_hub_wise.csv",
                                    mime="text/csv",
                                    key=f"same_day_dl_{month_name}"
                                )
                        
                        with col2:
                            if not next_day_all_hubs.empty:
                                csv_next_day = convert_df_to_csv(next_day_all_hubs)
                                st.download_button(
                                    label="Download Hub-wise Next Day Data (CSV)",
                                    data=csv_next_day,
                                    file_name=f"{month_name}_next_day_hub_wise.csv",
                                    mime="text/csv",
                                    key=f"next_day_dl_{month_name}"
                                )
                    
                    # Display Same Day table with full color formatting
                    st.subheader("Same Day Performance")
                    if not same_day_df.empty:
                        styled_same_day = format_dataframe(
                            same_day_df[['Date', 'Hub', 'Same day Orders', 'Attempted', 'Attempted %', 'Delivered', 'Delivered %']],
                            percentage_cols=['Attempted %', 'Delivered %']
                        )
                        st.dataframe(styled_same_day, use_container_width=True)
                    else:
                        st.info("No same day data available for the selected criteria")
                    
                    # Display Next Day table with full color formatting
                    st.subheader("Next Day Performance (Special Customers after 3PM only)")
                    if not next_day_df.empty:
                        styled_next_day = format_dataframe(
                            next_day_df[['Date', 'Hub', 'Next day Orders', 'Attempted', 'Attempted %', 'Delivered', 'Delivered %']],
                            percentage_cols=['Attempted %', 'Delivered %']
                        )
                        st.dataframe(styled_next_day, use_container_width=True)
                    else:
                        st.info("No next day data available for the selected criteria")
                    
                    # Show additional details in expander
                    with st.expander("Show Next Day Detailed Breakdown"):
                        st.write("""
                        - **Next Day Orders**: Special customer orders picked after 3PM previous day
                        - **Attempted Previous Day**: First attempt on same day as pickup (after 3PM)
                        - **Attempted Current Day**: First attempt on next day after pickup
                        - **Delivered Previous Day**: Delivered on same day as pickup (after 3PM)
                        - **Delivered Current Day**: Delivered on next day after pickup
                        """)
                        if not next_day_df.empty:
                            st.dataframe(next_day_df[['Date', 'Hub', 'Next day Orders', 
                                                  'Attempted Previous Day', 'Attempted Current Day',
                                                  'Delivered Previous Day', 'Delivered Current Day']])
                    
                    # Show comparison graphs if we have data
                    if not same_day_df.empty:
                        st.subheader("Performance Comparison")
                        plot_comparison(same_day_df, next_day_df, month_name, selected_hub)
                    
                    # Show hub-wise performance if "All" is selected and hub data exists
                    if selected_hub == "All" and has_hub_column:
                        st.subheader("Hub-wise Performance Summary")
                        hub_performance = process_hub_performance(month_data, hub_column)
                        if not hub_performance.empty:
                            styled_hub = format_dataframe(
                                hub_performance,
                                percentage_cols=['Avg Attempted %', 'Avg Delivered %']
                            )
                            st.dataframe(styled_hub, use_container_width=True)
                            
                            # Plot hub performance
                            plot_hub_performance(hub_performance, month_name)
                    
                    # Show customer-wise performance
                    st.subheader("Customer-wise Performance")
                    customer_performance = process_customer_performance(month_data)
                    if not customer_performance.empty:
                        # Display top 10 customers by volume
                        top_customers = customer_performance.nlargest(10, 'Total Orders')
                        styled_customers = format_dataframe(
                            top_customers,
                            percentage_cols=['Attempted %', 'Delivered %']
                        )
                        st.dataframe(styled_customers, use_container_width=True)
                        
                        # Plot customer performance
                        plot_customer_performance(customer_performance, month_name)
                else:
                    st.warning(f"No data available for {month_name}")

if __name__ == "__main__":
    main()
