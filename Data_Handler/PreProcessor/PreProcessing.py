import os
import glob
import pandas as pd


def find_csv_files(scrapers_folder):
    """Zoekt naar alle credit_cards.csv-bestanden in de Scrapers-map."""
    return glob.glob(os.path.join(scrapers_folder, '**', 'credit_cards.csv'), recursive=True)


def load_dataframes(csv_files):
    """Laadt CSV-bestanden in een lijst van DataFrames en filtert lege DataFrames eruit."""
    dataframes = [pd.read_csv(file) for file in csv_files]
    return [df for df in dataframes if not df.empty]


def merge_dataframes(dataframes):
    """Voegt een lijst van niet-lege DataFrames samen tot één DataFrame."""
    return pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()


def save_dataframe(df, output_file):
    """Slaat een DataFrame op als een CSV-bestand."""
    df.to_csv(output_file, index=False)
    print(f"✅ Data saved to {output_file}")


def categorize_columns(df):
    """Categoriseert kolommen en voegt categorieën toe aan het DataFrame."""
    category_mapping = {
        'Dining Benefits': [
            'Uncategorized - 6% Cashback: On dining includi',
            'Uncategorized - 7% Cashback: On dining and onl',
            'Uncategorized - 7% cashback on dining includin',
            'Uncategorized - Dine with up to 20% off at ove',
            'Cashback Dining'
        ],
        'Travel Benefits': [
            'Uncategorized - 10% cashback on airline ticket',
            'Uncategorized - 7% Cashback: On airlines ticke',
            'Uncategorized - 7% cashback on airline tickets',
            'Uncategorized - Complimentary airport lounge a',
            'Uncategorized - Airport Lounges: Complimentary',
            'Free Airport Transfers',
            'Lounge Access'
        ],
        'Shopping Benefits': [
            'Uncategorized - 10% cashback on hotel stays in',
            'Uncategorized - Cashback on hotel stays:',
            'Uncategorized - Cashback on airline tickets:',
            'Discount Fashion',
            'Discount Shopping',
            'Discount Flights',
            'Discount Hotels'
        ],
        'Financial Benefits': [
            'Uncategorized - Balance transfer\nTransfer your',
            'Uncategorized - Credit shield\nEnjoy compliment',
            'Uncategorized - 500 AED welcome bonus: as tala',
            'Uncategorized - 35% back on talabat orders: ap',
            'Uncategorized - Redeem talabat credit for tala',
            'Uncategorized - Mobile and digital wallets\nBen',
            'Uncategorized - School fee payments\nConvert sc',
            'Uncategorized - FlexiPay\nRepay balances in mon',
            'Uncategorized - Credit card loan\nBenefit from ',
            'Uncategorized - 6% Cashback: On dining includi',
            'Uncategorized - AED 365: As a welcome bonus',
            'Uncategorized - No Annual Fee: For the first y',
            'Uncategorized - 3% Cashback: On utilities, tel',
            'Uncategorized - 1% Cashback: On all other reta',
            'Uncategorized - 6% cashback on dining includin',
            'Uncategorized - 10% cashback on hotel stays in',
            'Uncategorized - Cashback on movie tickets purc',
            'Uncategorized - 10% cashback on airline ticket',
            'Uncategorized - Cashback on hotel stays:',
            'Uncategorized - Cashback on airline tickets:',
            'Uncategorized - 50% cashback on movies tickets',
            'Uncategorized - Foreign currency fees:',
            'Uncategorized - 5,000 monthly bonus: Etihad Gu',
            'Uncategorized - 60,000 Etihad Guest Miles: as ',
            'Uncategorized - Up to 4 class upgrade: voucher',
            'Uncategorized - 1 Etihad Tier Mile: per 1 USD',
            'Uncategorized - Up to 3 Etihad Guest Miles: pe',
            'Uncategorized - Up to 2 Class Upgrade Vouchers',
            'Uncategorized - 2,000 Etihad Guest Miles: as m',
            'Uncategorized - 1 Etihad Tier Mile: per USD 1',
            'Uncategorized - Up to 2 Etihad Guest Miles: pe',
            'Uncategorized - 35,000 Etihad Guest Miles: as ',
            'Uncategorized - Up to 1.25 Etihad Guest Miles:',
            'Uncategorized - Airport Lounges: Complimentary',
            'Uncategorized - 300,000 TouchPoints: As a welc',
            'Uncategorized - Free for life: No annual fees,',
            'Uncategorized - Buy 1 Get 1 Free movie ticket:',
            'Uncategorized - Zero-interest payment plan: on',
            'Uncategorized - Credit Card Loan\nBenefit from ',
            'Uncategorized - Complimentary airport lounge a',
            'Uncategorized - No annual fees:',
            'Uncategorized - 0% Interest Payment Plan: On s',
            'Uncategorized - Earn up to 3 Reward points fro',
            'Uncategorized - Earn 3 Reward points from ALL ',
            'Uncategorized - 7% Cashback: On hotel bookings',
            'Uncategorized - 7% Cashback: On dining and onl',
            'Uncategorized - 7% Cashback: On airlines ticke',
            'Uncategorized - 7% cashback on jewellery purc',
            'Uncategorized - 7% cashback on dining includin',
            'Uncategorized - 7% cashback on fuel',
            'Uncategorized - 7% cashback on spas and salons',
            'Uncategorized - 7% cashback on hotel spends',
            'Uncategorized - 7% cashback on jewellery purch',
            'Uncategorized - 7% Cashback: On fuel',
            'Uncategorized - 7% Cashback: On spas and salon',
            'Uncategorized - 1% Cashback: On all other dome',
            'Uncategorized - 7% Cashback: On health clubs a',
            'Uncategorized - PayOrder Facility\nReceive cash',
            'Uncategorized - PayOrder facility\nBenefit from',
            'Uncategorized - FlexiPay\nPay balances in month',
            'Uncategorized - 1 Tier Mile: per 1 USD',
            'Uncategorized - 2,000 monthly bonus: Etihad Gu',
            'Uncategorized - 35,000 Etihad Guest Miles: wel',
            'Uncategorized - Up to 2 class upgrade: voucher',
            'Uncategorized - Free for life: no annual fee, ',
            'Uncategorized - Unlimited free delivery: on ta'
        ]
    }

    for category, keywords in category_mapping.items():
        df[category] = df.apply(lambda row: any(keyword in str(row.values) for keyword in keywords), axis=1)

    return df


def main():
    scrapers_folder = '../Scrape Data/Scrapers'
    merged_output_file = 'merged_credit_cards.csv'
    categorized_output_file = 'categorized_credit_cards.csv'

    csv_files = find_csv_files(scrapers_folder)
    dataframes = load_dataframes(csv_files)

    if not dataframes:
        print("⚠️ No non-empty CSV files found.")
        return

    merged_df = merge_dataframes(dataframes)
    save_dataframe(merged_df, merged_output_file)

    categorized_df = categorize_columns(merged_df)
    save_dataframe(categorized_df, categorized_output_file)


if __name__ == "__main__":
    main()
