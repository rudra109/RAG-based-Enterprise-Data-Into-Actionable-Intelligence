import csv
import random
import math
from datetime import datetime, timedelta

def generate_ecommerce_sales(filename="large_ecommerce_sales.csv", rows=25000):
    print(f"Generating {filename}...")
    categories = ["Electronics", "Clothing", "Home", "Sports", "Toys"]
    start_date = datetime(2021, 1, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "transaction_id", "user_id", "product_category", "price", "qty", "total_revenue", "discount_applied"])
        
        for i in range(rows):
            # Advance time by a few minutes per transaction
            start_date += timedelta(minutes=random.randint(5, 60))
            cat = random.choice(categories)
            price = round(random.uniform(10, 500), 2)
            qty = random.randint(1, 5)
            discount = round(random.uniform(0, 0.3), 2) if random.random() > 0.7 else 0.0
            
            # Anomaly injection: massive bulk order every 5000 rows
            if i > 0 and i % 5000 == 0:
                qty = random.randint(100, 500)
            
            total = round(price * qty * (1 - discount), 2)
            writer.writerow([
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                f"TXN-{100000+i}",
                f"USR-{random.randint(1000, 9999)}",
                cat, price, qty, total, discount
            ])

def generate_server_metrics(filename="large_server_metrics.csv", rows=50000):
    print(f"Generating {filename}...")
    servers = ["SRV-01", "SRV-02", "SRV-03", "SRV-04"]
    start_date = datetime(2023, 1, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "server_id", "cpu_usage_pct", "memory_usage_mb", "disk_io_ops", "network_rx_kbps"])
        
        for i in range(rows):
            # 5 minute intervals
            start_date += timedelta(minutes=5)
            server = servers[i % len(servers)]
            
            # Normal distribution base
            cpu = max(1, min(99, random.gauss(35, 10)))
            mem = max(500, min(16000, random.gauss(4000, 500)))
            disk = max(10, random.gauss(150, 40))
            net = max(100, random.gauss(5000, 1000))
            
            # Anomaly injection: Server 02 crashes randomly
            if server == "SRV-02" and random.random() < 0.001:
                cpu = 99.9
                mem = 15900
                disk = 15000
                net = 0
                
            writer.writerow([
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                server,
                round(cpu, 2),
                round(mem, 2),
                round(disk, 2),
                round(net, 2)
            ])

def generate_marketing_campaigns(filename="large_marketing_campaigns.csv", rows=15000):
    print(f"Generating {filename}...")
    platforms = ["Google Ads", "Facebook", "LinkedIn", "TikTok"]
    start_date = datetime(2022, 6, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "campaign_id", "platform", "ad_spend", "impressions", "clicks", "conversions", "cost_per_acquisition"])
        
        for i in range(rows):
            start_date += timedelta(hours=random.randint(1, 4))
            platform = random.choice(platforms)
            spend = round(random.uniform(50, 5000), 2)
            impressions = int(spend * random.uniform(10, 100))
            clicks = int(impressions * random.uniform(0.01, 0.05))
            conversions = int(clicks * random.uniform(0.02, 0.1))
            
            # Prevent div by zero
            cpa = round(spend / conversions, 2) if conversions > 0 else spend
            
            writer.writerow([
                start_date.strftime("%Y-%m-%d"),
                f"CAMP-{1000+i}",
                platform, spend, impressions, clicks, conversions, cpa
            ])

def generate_iot_sensors(filename="large_iot_sensors.csv", rows=60000):
    print(f"Generating {filename}...")
    start_date = datetime(2023, 9, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "sensor_id", "temperature_c", "humidity_pct", "vibration_hz"])
        
        for i in range(rows):
            start_date += timedelta(minutes=1)
            # Sine wave pattern for temp
            time_factor = (i % 1440) / 1440.0 # Daily cycle
            temp = 20 + 10 * math.sin(time_factor * 2 * math.pi) + random.uniform(-2, 2)
            hum = 50 + 20 * math.cos(time_factor * 2 * math.pi) + random.uniform(-5, 5)
            vib = random.uniform(10, 50)
            
            # Anomaly injection: sudden vibration spike indicating machine failure
            if i > 0 and i % 12000 == 0:
                vib = random.uniform(500, 1000)
                temp += 50
                
            writer.writerow([
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                f"SENS-{random.randint(1, 5)}",
                round(temp, 2),
                round(hum, 2),
                round(vib, 2)
            ])

def generate_financial_stocks(filename="large_financial_stocks.csv", rows=20000):
    print(f"Generating {filename}...")
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "ticker", "open_price", "high", "low", "close_price", "volume"])
        
        for ticker in tickers:
            current_price = random.uniform(50, 300)
            start_date = datetime(2015, 1, 1)
            for i in range(rows // len(tickers)):
                start_date += timedelta(days=1)
                if start_date.weekday() >= 5: continue # Skip weekends
                
                volatility = random.uniform(0.005, 0.03)
                open_p = current_price * (1 + random.uniform(-0.01, 0.01))
                close_p = open_p * (1 + random.uniform(-volatility, volatility))
                high = max(open_p, close_p) * (1 + random.uniform(0, 0.02))
                low = min(open_p, close_p) * (1 - random.uniform(0, 0.02))
                volume = int(random.uniform(1000000, 50000000))
                
                current_price = close_p
                writer.writerow([
                    start_date.strftime("%Y-%m-%d"),
                    ticker,
                    round(open_p, 2), round(high, 2), round(low, 2), round(close_p, 2), volume
                ])

def generate_hr_attrition(filename="large_hr_attrition.csv", rows=10000):
    print(f"Generating {filename}...")
    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance"]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["employee_id", "department", "years_at_company", "satisfaction_score", "last_evaluation", "salary_usd", "left_company"])
        
        for i in range(rows):
            dept = random.choice(departments)
            years = random.randint(1, 15)
            sat = round(random.uniform(1.0, 5.0), 1)
            eval_score = round(random.uniform(1.0, 5.0), 1)
            salary = random.randint(50000, 200000)
            
            # Likelihood of leaving increases with low satisfaction and high years without high pay
            leave_prob = 0.1
            if sat < 2.5: leave_prob += 0.4
            if years > 5 and salary < 80000: leave_prob += 0.3
            
            left = 1 if random.random() < leave_prob else 0
            
            writer.writerow([
                f"EMP-{1000+i}", dept, years, sat, eval_score, salary, left
            ])

def generate_supply_chain(filename="large_supply_chain.csv", rows=30000):
    print(f"Generating {filename}...")
    hubs = ["NY", "LA", "Chicago", "Houston", "Miami", "Seattle"]
    start_date = datetime(2022, 1, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "shipment_id", "origin", "destination", "weight_kg", "cost_usd", "transit_time_days", "is_delayed"])
        
        for i in range(rows):
            start_date += timedelta(hours=random.randint(1, 6))
            origin = random.choice(hubs)
            dest = random.choice([h for h in hubs if h != origin])
            weight = round(random.uniform(10, 5000), 2)
            cost = round(weight * random.uniform(0.5, 2.5), 2)
            transit = random.randint(1, 14)
            
            # Anomaly: Chicago gets massively delayed due to winter storm in simulation
            delay_prob = 0.05
            if origin == "Chicago" and start_date.month in [1, 2]:
                delay_prob = 0.6
                transit += random.randint(5, 10)
                
            delayed = 1 if random.random() < delay_prob else 0
            
            writer.writerow([
                start_date.strftime("%Y-%m-%d"),
                f"SHP-{100000+i}",
                origin, dest, weight, cost, transit, delayed
            ])

def generate_customer_support(filename="large_customer_support.csv", rows=20000):
    print(f"Generating {filename}...")
    categories = ["Billing", "Technical", "Account", "Refunds"]
    start_date = datetime(2023, 1, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "ticket_id", "category", "resolution_time_hrs", "customer_satisfaction", "agent_id"])
        
        for i in range(rows):
            start_date += timedelta(hours=random.randint(1, 3))
            cat = random.choice(categories)
            res_time = round(random.uniform(0.5, 72.0), 1)
            sat = random.randint(1, 5)
            
            # Anomaly: Technical tickets start taking 300+ hours near end of dataset
            if cat == "Technical" and i > 18000:
                res_time = round(random.uniform(200, 500), 1)
                sat = 1
                
            writer.writerow([
                start_date.strftime("%Y-%m-%d"),
                f"TCK-{10000+i}",
                cat, res_time, sat, f"AGT-{random.randint(10, 50)}"
            ])

if __name__ == "__main__":
    generate_ecommerce_sales()
    generate_server_metrics()
    generate_marketing_campaigns()
    generate_iot_sensors()
    generate_financial_stocks()
    generate_hr_attrition()
    generate_supply_chain()
    generate_customer_support()
    print("All 8 massive datasets generated successfully!")
