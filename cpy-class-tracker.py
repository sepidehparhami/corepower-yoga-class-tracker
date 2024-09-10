import glob
from bs4 import BeautifulSoup
import pandas as pd
import re
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import datetime
import calendar
import os
import markdown

from shiny import App, ui, run_app, render, reactive

os.chdir('/Users/sepideh/Library/CloudStorage/GoogleDrive-sepidehparhami@gmail.com/My Drive/Data Science/Projects/corepower-yoga-class-tracker')

def make_class_df(class_divs):
  cols = ['date_string',
         'time',
         'timezone',
         'title',
         'location',
         'teacher']
  
  class_df = pd.DataFrame(columns=cols, index=[])
  
  for i, class_div in enumerate(class_divs):
    date = class_div.find('div', class_='subtitle2 color-grey3 letter-spacing-1').text
    time = class_div.find('div', class_='subtitle2 text-nowrap').text
    timezone = class_div.find('div', class_='subtitle2 color-grey2 font-semibold ml-2').text
    title = class_div.find('div', class_='body-1').text
    location = class_div.find('div', class_='subtitle2 font-semibold color-grey4 align-self-center').text
    teacher_found = class_div.find('a', class_='link body-2 link-grey d-inline')
    if teacher_found:
      teacher = teacher_found.text
    else:
      teacher = 'No teacher listed'
                      
    to_append = pd.Series([date, time, timezone, title, location, teacher], index=cols).to_frame().T
    class_df = pd.concat([class_df, to_append], ignore_index=True)

  return class_df

def add_cols_to_df(class_df):
  month_dict = {month: index for index, month in enumerate(calendar.month_abbr) if month}

  separated_dates = [x.split(', ') for x in class_df['date_string']]
  class_df['day_of_week'] = [x[0] for x in separated_dates]
  class_df['year'] = [int(x[2]) for x in separated_dates]
  month_name = [x[1] for x in separated_dates]
  class_df['month'] = [month_dict[x.split(' ')[0]] for x in month_name]
  class_df['day'] = [int(x.split(' ')[1]) for x in month_name]
  class_df['start_time'] = [x.split(' ')[0] for x in class_df['time']]
  class_df['am_pm'] = [x.split(' ')[1] for x in class_df['time']]
  class_df['start_hour'] = [' '.join([x.split(':')[0], class_df['am_pm'][i]]) for i, x in enumerate(class_df['start_time'])]
  
  class_df['date'] = [datetime.datetime(x['year'], x['month'], x['day'], int(x['start_time'].split(':')[0]), int(x['start_time'].split(':')[1])) for _, x in class_df.iterrows()]
  class_df['month_year'] = [x.strftime('%b %Y') for x in class_df['date']]
  class_df['week_number'] = [int(x.strftime('%V')) for x in class_df['date']]
  class_df['year_week'] = [x['year']*100 + x['week_number'] for _, x in class_df.iterrows()]

  return class_df

def compute_stats(class_df):
  stats_str = ''
  
  total = len(class_df)
  stats_str += f'total number of classes: {total}\n'

  number_of_weeks = (datetime.datetime.today() - min(class_df['date'])).days // 7
  avg_classes_per_week = total / number_of_weeks
  stats_str += f'average number of classes per week: {avg_classes_per_week:.1f}\n'
  
  week_counts = class_df['year_week'].value_counts()
  highest_classes_week = week_counts.iloc[0]
  highest_week = week_counts.index[0]
  stats_str += f'highest number of classes in a week: {highest_classes_week} in {highest_week}\n'
  
  month_counts = class_df['month_year'].value_counts()
  highest_classes_month = month_counts.iloc[0]
  highest_month = month_counts.index[0]
  stats_str += f'highest number of classes in a month: {highest_classes_month} in {highest_month}\n'
  
  day_counts = class_df['date_string'].value_counts()
  highest_classes_day = day_counts.iloc[0]
  highest_day = day_counts.index[0]
  stats_str += f'highest number of classes in a day: {highest_classes_day} on {highest_day}\n'
  
  hours_count = class_df['start_hour'].value_counts()
  most_freq_hour = hours_count.index[0]
  number_classes_hour = hours_count.iloc[0]
  stats_str += f'most frequent hour of day: {most_freq_hour} ({number_classes_hour} classes)\n'

  teacher_count = class_df['teacher'].value_counts()
  most_freq_teacher = teacher_count.index[0]
  number_classes_teacher = teacher_count.iloc[0]
  stats_str += f'most frequent teacher: {most_freq_teacher} ({number_classes_teacher} classes)\n'

  return stats_str

app_ui = ui.page_fluid(
    ui.navset_tab(
      ui.nav_panel('Input Data',
              ui.card(
                ui.markdown('''
                    # Corepower Yoga Class Tracker
                    Note: the app developer is not affiliated with Corepower Yoga.
                    
                    This app scrapes information from your Corepower Yoga class history to make graphs and compute statistics about the classes you have taken.
                    
                    ## How to use this app
                    Go to <a href="https://www.corepoweryoga.com/profile/activity/default" target="_blank">https://www.corepoweryoga.com/profile/activity/default</a>\n
                    Click the black and white person icon in the top right and click "SIGN IN."
                    '''),
                ui.output_image('log_in'),
                ui.markdown('''
                    When you get to your Class History page, click the rectangle containing a date range and a calendar will appear. Select the option for "All time" at the bottom. 
                    '''),
                ui.output_image('get_to_all_classes'),
                ui.markdown('''
                    Right click anywhere on the page and select "Save As..."
                    '''),
                ui.output_image('save_html_1'),
                ui.markdown('''
                    Use the default format of "Webpage, Complete" and change the default file name to something like "cpy_class_history" and click "Save."
                    '''),
                ui.output_image('save_html_2'),

                
                ui.input_file('html_file', "Choose the .html file you saved", accept=['.html'], multiple=False),
                ui.output_text('valid'),
              )
      ),
      
       ui.nav_panel('Analysis',
        ui.card(ui.output_text_verbatim('stats_str')),
        ui.card(ui.output_plot('p_location'))),
      
      ui.nav_panel('Download CSV',
        ui.card(
          ui.download_button("download", "Download CSV"),
          ui.layout_columns(ui.card(ui.output_data_frame('summary_data'))),
            )
      )),
      id='Page',
      
)
    
    
    

def server(input, output, session):
    
    @render.image
    def log_in():
      return {'src': os.getcwd() + '/images/log_in.png', 'width': '700px'}
    
    @render.image
    def get_to_all_classes():
      return {'src': os.getcwd() + '/images/get_to_all_classes.png', 'width': '700px'}
    
    @render.image
    def save_html_1():
      return {'src': os.getcwd() + '/images/save_html_1.png', 'width': '700px'}

    @render.image
    def save_html_2():
      return {'src': os.getcwd() + '/images/save_html_2.png', 'width': '600px'}
    
    # # TODO: switch to plots tab automatically once file has been uploaded
    # @reactive.Effect
    # @reactive.event(input.html_file)
    # def _():
    #   ui.update_navs(
    #       'Page', selected='Plots'
    #     )
    
    @render.text
    @reactive.event(input.html_file)
    def valid():
      url = re.search('https://www.corepoweryoga.com/profile/activity/default', str(get_soup()))
      if url is not None:
        return 'File is valid. Proceed to view stats and plots in Analysis tab.'
      else:
        return 'Error: file is invalid'
      
    @reactive.calc
    def get_soup():
      if input.html_file() is None:
        return
      
      input_file = input.html_file()[0]['datapath']
      with open(input_file) as f:
        return BeautifulSoup(f, 'html.parser')

    @reactive.calc
    def parse_data():
      soup = get_soup()
      class_divs = soup.find_all('div', class_='d-flex flex-column p-3 py-4 px-sm-4 mt-3 border rounded-lg')
      return make_class_df(class_divs)
    
    @reactive.calc
    def df_cols_added():
      return add_cols_to_df(parse_data())
    
    @render.data_frame
    def summary_data():
      return render.DataGrid(parse_data(), selection_mode="rows")

    @render.text
    def stats_str():
      return compute_stats(df_cols_added())


    



    @render.plot
    def p_location():
      fig, ax = plt.subplots(figsize=(15,10))
      sns.countplot(x='location', data=df_cols_added(), color='orange', order=parse_data()['location'].value_counts().index, ax=ax)
      for container in ax.containers:
          ax.bar_label(container)
      plt.xticks(rotation=-45, ha='left')
      plt.title('Number of Classes by Location')
      return fig

    @session.download(filename='corepower_data.csv')
    def download():
        return parse_data().to_csv()

app = App(app_ui, server)
run_app(app)
