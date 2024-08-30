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

def make_class_df(class_divs):
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



app_ui = ui.page_fluid(
    ui.navset_tab(
      ui.nav_panel('Input Data',
              ui.card(
                ui.output_text('intro'),
                ui.input_file('html_file', "Choose HTML file", accept=['.html'], multiple=False),
                ui.output_text('valid'),
              )
      ),
      
       ui.nav_panel('Plots',
        ui.card(ui.output_plot('p'))),
  
      
      ui.nav_panel('Download CSV',
        ui.card(ui.layout_columns(ui.card(ui.output_data_frame('summary_data'))),
            ui.download_button("download", "Download CSV"),)
      )),
      id='Page'
      
)
    
    
    

def server(input, output, session):
    @render.text
    def intro():
      return 'Log into your Corepower Yoga account and go to https://www.corepoweryoga.com/profile/activity/default (icon with your initials in top right > Class History). Click the date range and select "All time." Right click anywhere on page > save as Webpage (html only)'
    
    @reactive.Effect
    @reactive.event(input.html_file)
    def update_tab():
      ui.update_navs(
          'Page', selected='Plots'
        )
    
    @render.text
    def valid():
      url = re.search('https://www.corepoweryoga.com/profile/activity/default', str(get_soup()))
      if url is not None:
        return
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

    
    
    @render.data_frame
    def summary_data():
      return render.DataGrid(parse_data(), selection_mode="rows")

    @render.plot
    def p():
      fig, ax = plt.subplots(figsize=(15,10))
      sns.countplot(x='location', data=parse_data(), color='orange', order=parse_data()['location'].value_counts().index, ax=ax)
      for container in ax.containers:
          ax.bar_label(container)
      plt.xticks(rotation=-45, ha='left')
      plt.title('Number of Classes by Location')
      return fig

    @session.download(filename="data.csv")
    def download():
        return parse_data().to_csv()

app = App(app_ui, server)
run_app(app)
