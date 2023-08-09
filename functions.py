import pandas as pd
import datetime
from faker import Faker

def clean_dataframe(dataframe):
    cleaned_dataframe = dataframe.applymap(lambda x: x.strip().capitalize() if isinstance(x, str) else x)
    return cleaned_dataframe


def generate_synthetic_data(num_rows, start_date, end_date):
    fake = Faker()
    columns = ['Surname', 'Given Name', 'Date of Birth', 'Sex', 'Postal Address', 'Post Code', 'Date of Test1']
    data = []

    for _ in range(num_rows):
        sex = fake.random_element(elements=('Male', 'Female', 'Other'))
        if sex == 'Male':
            given_name = fake.first_name_male()
        elif sex == 'Female':
            given_name = fake.first_name_female()
        else:
            given_name = fake.first_name()
            
        surname = fake.last_name()
        date_of_birth = fake.date_of_birth(minimum_age=50, maximum_age=74).strftime('%dd-%mm-%YYYY')
        postal_address = fake.address()
        postal_code = fake.postcode()
        date_of_test1 = fake.date_between_dates(date_start=start_date, date_end=end_date).strftime('%d-%m-%Y')

        data.append([surname, given_name, date_of_birth, sex, postal_address, postal_code, date_of_test1])

    df = pd.DataFrame(data, columns=columns)
    return df

def deidentify_data(df):
    fake = Faker()
    df['personal_id'] = [fake.uuid4() for _ in range(len(df))]
    df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], format='%d/%m/%Y').strftime('%m-%Y')
    df = df.drop(columns=['Surname', 'Given Name'])
    return df