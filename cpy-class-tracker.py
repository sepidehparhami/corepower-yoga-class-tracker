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

from shiny import App, Inputs, Outputs, Session, ui, run_app, render, reactive


app_ui = ui.page_fluid(
    ui.output_text('intro'),
    ui.input_file('html_file', "Choose HTML file", accept=['.html'], multiple=False),
    ui.output_text('valid'),
    ui.layout_columns(ui.card(ui.output_data_frame('summary_data'))),
    ui.download_button("download", "Download CSV"),
    ui.output_plot('p'))

def server(input: Inputs, output: Outputs, session: Session):
    @render.text
    def intro():
      return 'Log into your Corepower Yoga account and go to https://www.corepoweryoga.com/profile/activity/default (icon with your initials in top right > Class History). Click the date range and select "All time." Right click anywhere on page > save as Webpage (html only)'
    
    @render.text
    def valid():
      t = re.search('https://www.corepoweryoga.com/profile/activity/default', str(get_soup()))
      if t is not None:
        return 'valid file'
      else:
        return 'invalid file'
      
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
  
      cols = ['date',
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

    
    
    @render.data_frame
    def summary_data():
        return render.DataGrid(parse_data(), selection_mode="rows")

    @render.plot
    def p():
      fig, ax = plt.subplots(figsize=(15,10))
      sns.countplot(x='location', data=parse_data(), color='orange', order=class_df['location'].value_counts().index, ax=ax)
      for container in ax.containers:
          ax.bar_label(container)
      plt.xticks(rotation=-45, ha='left')
      plt.title('Number of Classes by Location')
      return fig

    @session.download(filename="data.csv")
    def download():
        yield parse_data().to_csv()

app = App(app_ui, server)
run_app(app)
