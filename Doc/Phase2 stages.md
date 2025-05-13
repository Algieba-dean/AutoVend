# Phase2 stages

## Data preparation

depends on the interface, which label/slots we support, we should have such a list


### User profile data

- basic information

	- telephone

	- age

	- gender

	- appellation/title

	  称呼
	  
		- Mr.

		- Mrs.

		- Miss

		- Ms.

		- AutoVend should ask

	- target driver

		- self

		- wife

		- parents

		- both

	- expertise

		- 1-10

- additional information

	- Family size

		- Children count

	- price sensivity

		- high

		- medium

		- low

	- residence

		- country

		- province

		- city

	- parking conditions

		- allocated parking space

		- temporary parking allowed

		- charging pile facilites available

### Precise Needs

直接取出值，然后所有取出值用“与”逻辑做搜索

- prize

	- Below 10,000

		- Cheap

	- 10,000 ~ 20,000

		- Economy

	- 20,000 ~ 30,000

		- Mid-Range Low-End

	- 30,000 ~ 40,000

		- Mid-Range

	- 40,000 ~ 60,000

		- Mid-Range High-End

	- 60,000 ~ 100,000

		- High-End

	- Above 100,000

		- Luxury

- Vehicle Basic Information

	- Vehicle Category

		- Sedan

			- Small Sedan

				- Micro Sedan

				- Compact Sedan

			- Mid-Size Sedan

				- B-Segment Sedan

			- Mid-Large Sedan

				- C-Segment Sedan

				- D-Segment Sedan

		- SUV

			- Crossover SUV

				- Compact SUV

				- Mid-Size SUV

				- Mid-to-Large SUV

			- Body-on-frame SUV

				- Off-road SUV

				- All-terrain SUV

		- MPV

			- Family MPV

				- Compact MPV

				- Mid-Size MPV

				- Large MPV

			- Business MPV

				- Mid-Size Business MPV

				- Large-Size Busness MPV

		- Sprots Car

			- Convertible Sports Car

				- Two-door Convertible Sports  Car

				- Four-door Convertible Sports Car

			- Hardtop Sports Car

				- Two-door Hardtop Sports Car

				- Four-door Hardtop Sports Car

	- Brand

	  Need some specific handling to search
	  e.g. brand=European -> brand=Germany + 
	  
		- European

			- Germany


				- Volkswagen

				- Audi

				- Porsche

				- Bentley

				- Bugatti

				- Lamborghini

				- BMW

				- Mercedes-Benz

			- France

				- Peugeot

				- Renault

			- United Kingdom

				- Jaguar

				- Land Rover

				- Rolls-Royce

			- Sweden

				- Volvo

		- American

			- USA

				- Chevrolet

				- Buick

				- Cadillac

				- Ford

				- Tesla

		- Asian

			- Japan

				- Toyota

				- Honda

				- Nissan

				- Suzuki

				- Mazda

			- Korea

				- Hyundai

			- China

				- BYD

				- Geely

				- Changan

				- Great Wall Motor

				- Nio

				- XiaoMi

				- XPeng

	- Powertrain Type

		- Fuel

			- Gasoline Engine

			- Diesel Engine

		- Hybrid

			- Hybrid Electric Vehicle

			- Plug-in Hybird Electric Vehicle

			- Range-Extended Electric Vehicle

		- Battery Electric

			- Battery Electric Vehicle

	- Vehicle Dimensions

		- Passenger Space Volume

			- 2.5-3.5 m³

				- Small Space

			- 3.5-4.5 m³

				- Medium Space

			- 4.5-5.5  m³

				- Large Space

			- Above 5.5  m³

				- Luxury Space

		- Trunk Volume

			- 200 - 300L

				- Small

			- 300-400L

				- Medium

			- 400-500L

				- Large

			- Above 500L

				- Luxury

		- Wheelbase

			- 2300-2650mm

				- Small

			- 2650-2800mm

				- Moderate

			- 2800-2950mm

				- Spacious

			- 2950-3100mm

				- Very Spacious

			- Above 3100mm

				- Luxury Spacious

		- Chassis Height

			- Low Ride Height

				- 100-130mm

			- Medium Ride Height

				- 130-150mm

			- High Ride Height

				- 150-200mm

			- Off-road Chassis

				- Above 200mm

- Exterior and Interior

	- Exterior

		- Design Style

			- Sporty

			- Business

		- Body Line Smoothness

			- High

			- Medium

			- Low

		- Color

			- Bright Colors

			- Neutral Colors

			- Dark Colors

	- Interior

		- Interior Material Texture

			- Wood Trim

			- Metal Trim

- Configuration Parameters

	- Safety Features

		- ABS

			- Yes

			- No

		- ESP

			- Yes

			- No

		- Airbag Count

			- Low Trim

				- 2

				- 4

			- Mid Trim

				- 6

				- 8

			- High Trim

				- 10

				- Above 10

	- Comfort Features

		- Seat Material

			- Leather

			- Fabric

		- Noise Insulation

			- High

			- Medium

			- Low

	- Smart Features

		- Infotainment System

			- Voice Interaction

				- Yes

				- No

			- OTA Updates

				- Yes

				- No

		- Autonomous Driving Level

			- L2

			- L3

		- Adaptive Cruise Control

			- Yes

			- No

		- Traffic Jam Assist

			- Yes

			- No

		- Automatic Emergency Braking

			- Yes

			- No

		- Lane Keep Assist

			- Yes

			- No

		- Remote Parking

			- Yes

			- No

		- Auto Parking

			- Yes

			- No

		- Blind-Spot Detection

			- Yes

			- No

		- Fatigue Driving Detection

			- Yes

			- No

		- Smartphone Integration

			- CarPlay

			- Andriod Auto

- Performance Parameters

	- Powertrain System

		- Engine Displacement

			- Small

				- Below 1.0L

				- 1.0-1.6L

			- Medium

				- 1.6-2.0L

				- 2.0-2.5L

			- Large

				- 2.5-3.5L

				- 3.5-6.0L

			- Extra-Large

				- Above 6.0L

			- None

				- For Battery Electoric Vehicel

		- Motor Power

			- Low

				- Below 70kW

			- Lower-Medium

				- 70-120kW

			- Medium

				- 120-180kW

			- Higher-Medium

				- 180-250kW

			- High

				- 250-400kW

			- Extra-High

				- Above 400kW

		- Battery Capacity

			- Small

				- 30-50kWh

			- Medium

				- 50-80kWh

			- Large

				- 80-100kWh

			- Extra-Large

				- Above 100kWh

			- None

				- for Gasoline Engine or Diesel Engine

		- Fuel Tank Capacity

			- Small

				- 30-50L

			- Medium

				- 50-70L

			- Large

				- Above 70L

			- None

				- For Battery Electric Vehicle

		- Horsepower

			- Low

				- Below 100 hp

			- Lower-Medium

				- 100-200 hp

			- Medium

				- 200-300 hp

			- High

				- 300-400 hp

			- Extra-High

				- Above 400 hp

		- Torque

			- Low

				- 200N·m

			- Lower-Medium

				- 200-300 N·m

			- Medium

				- 300-400 N·m

			- High

				- 400-500 N·m

			- Extra-High

				- Above 500 N·m

	- Driving Performance

		- 0–100 km/h Acceleration Time

			- Slow

				- Above 10s

			- Medium

				- 8-10s

			- Fast

				- 6-8s

			- Very Fast

				- 4-6s

			- Extreme

				- Below 4s

		- Top Speed

			- Low

				- Below 160KM/h

			- Medium

				- 160-200KM/h

			- High

				- 200-240km/h

			- Very High

				- 240-300km/h

			- Extreme

				- Above 300km/h

	- Energy Consumption

		- Fuel Consumption

			- Low

				- 4-6L/100km

			- Medium

				- 6-8L/100km

			- High

				- Above 8L/100km

			- None

				- For Battery Electric Vehicle

		- Electric Consumption

			- Low

				- 10-12kWh/100km

			- Medium

				- 12-14kWh/100km

			- High

				- Above 14kWh/100km

			- None

				- for Gasoline Engine or Diesel Engine

		- Driving Range

			- Short

				- 300-400km

			- Medium

				- 400-800km

			- Long

				- Above 800km

	- Handling

		- Drive Type

			- Front-Wheel Drive

			- Rear-Wheel Drive

			- All-Wheel Drive

		- Suspension

			- Suspension

			- Non-independent

		- Passability

			- Low

			- Medium

			- High

- Space and Practicality

	- Passenger Space

		- Seat Layout

			- 5-seat

			- 7-seat

- Use Scenarios

	- Commuting Needs

		- City Commuting

			- Yes

			- No

		- Highway Long-Distance

			- Yes

			- No

	- Special Scenarios

		- Off-road Capability

			- Low

			- Medium

			- High

		- Cargo Capability

			- Yes

			- No

		- Cold-Resistance

			- Low

			- Medium

			- High

		- Heat-Resistance

			- Low

			- Medium

			- High

### Ambiguous Needs

取最高子树，所有取出的label，用“或”逻辑去搜索

- Size

	- Small

	- Medium

	- Large

- Vehicle Usability

	- Low

	- Medium

	- High

- Aesthetics

	- Low

	- Medium

	- High

- Energy Consumption Level

	- Low

	- Medium

	- High

- Comfort Level

	- Low

	- Medium

	- High

- Smartness

	- Low

	- Medium

	- High

- Family-Friendliness

	- Low

	- Medium

	- High

### dialog data

## Train model

### user profile model

### explicit needs model

### implicit needs model

### dialog model

## 模型训练

## 分支主题 3

## 需求

### 显性

- 尺寸大的

	- 模糊

- 宝马3系

	- 精确

### 隐性

- 想看星空

	- 天窗

		- 精确

- 人口多

	- 尺寸大

		- 模糊

