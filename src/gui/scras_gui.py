#!/usr/local/bin/python3

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from functools import reduce, partial
import os
import sys
import platform
import pandas as pd
import tkinter as tk
import numpy as np
from tkinter import filedialog, ttk
import phenograph
import csv

sys.path.insert(0, '/Users/vincentliu/PycharmProjects/magic/src/magic')
import mg_new as mg


class SCRASGui(tk.Tk):
    def __init__(self, parent):
        tk.Tk.__init__(self, parent)
        self._parent = parent

        self.menubar = tk.Menu(self)
        self.fileMenu = tk.Menu(self.menubar, tearoff=0)
        self.analysisMenu = tk.Menu(self.menubar, tearoff=0)
        self.visMenu = tk.Menu(self.menubar, tearoff=0)

        self.vals = None
        self.currentPlot = None
        self.data = {}

        self.initialize()

    # updated
    def initialize(self):
        self.grid()

        # set up menu bar
        self.menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label="Load csv file", command=self.load_csv)
        self.fileMenu.add_command(label="Load sparse data file", command=self.load_mtx)
        self.fileMenu.add_command(label="Load 10x file", command=self.load_10x)
        self.fileMenu.add_command(label="Load saved session from pickle file", command=self.load_pickle)
        self.fileMenu.add_command(label="Concatenate datasets", state='disabled', command=self.concatenate_data)
        self.fileMenu.add_command(label="Save data", state='disabled', command=self.save_data)
        self.fileMenu.add_command(label="Save plot", state='disabled', command=self.save_plot)
        self.fileMenu.add_command(label="Exit", command=self.quit_scras())

        self.menubar.add_cascade(label="Analysis", menu=self.analysisMenu)
        self.analysisMenu.add_command(label="Dimensionality Reduction", state='disabled', command=self.run_dr)
        self.analysisMenu.add_command(label="Clustering", state='disabled', command=self.run_clustering)
        self.analysisMenu.add_command(label="Gene Expression Analysis", state='disabled', command=self.run_gea)

        self.menubar.add_cascade(label="Visualization", menu=self.visMenu)
        self.visMenu.add_command(label="tSNE", state='disabled', command=self.tsne)
        self.visMenu.add_command(label="Scatter plot", state='disabled', command=self.scatter_plot)

        self.config(menu=self.menubar)

        # intro screen
        tk.Label(self, text="SCRAS", font=('Helvetica', 48), fg="black", bg="white",
                 padx=100, pady=10).grid(row=0)
        tk.Label(self, text="Single Cell RNA Analysis Suite", font=('Helvetica', 25), fg="black",
                 bg="white", padx=100, pady=5).grid(row=1)
        tk.Label(self, text="To get started, select a data file by clicking File > Load Data", fg="black", bg="white",
                 padx=100, pady=25).grid(row=2)

        # update
        self.protocol('WM_DELETE_WINDOW', self.quit_scras())
        self.grid_columnconfigure(0, weight=1)
        self.resizable(True, True)
        self.update()
        self.geometry(self.geometry())
        self.focus_force()

    def load_csv(self):
        filename = filedialog.askopenfilename(title='Load data file', initialdir='~/.magic/data')

        if filename:
            import_options = tk.Toplevel()
            import_options.title('Data options')
            tk.Label(import_options, text="File name: ", pady=5).grid(column=0, row=0)
            tk.Label(import_options, text=filename.split('/')[-1], pady=5).grid(column=1, row=0)

            tk.Label(import_options, text="Data name: ").grid(column=0, row=1)
            fileNameEntryVar = tk.StringVar()
            fileNameEntryVar.set('Data ' + str(len(self.data) + 1))
            tk.Entry(import_options, textvariable=fileNameEntryVar).grid(column=1, row=1)

            tk.Label(import_options, text="Delimiter: ").grid(column=0, row=2)
            delimiter = tk.StringVar()
            delimiter.set(',')
            tk.Entry(import_options, textvariable=delimiter).grid(column=1, row=2)

            tk.Label(import_options, text="Rows:", fg="black", bg="white").grid(column=0, row=3)
            rowVar = tk.IntVar()
            rowVar.set(0)
            tk.Radiobutton(import_options, text="Cells", variable=rowVar, value=0).grid(column=1, row=3, sticky='W')
            tk.Radiobutton(import_options, text="Genes", variable=rowVar, value=1).grid(column=2, row=3, sticky='W')

            tk.Label(import_options, text="Number of additional rows/columns to skip after gene/cell names").grid(
                     column=0, row=4, columnspan=3)

            tk.Label(import_options, text="Number of rows:").grid(column=0, row=5)
            rowHeader = tk.IntVar()
            rowHeader.set(0)
            tk.Entry(import_options, textvariable=rowHeader).grid(column=1, row=5)

            tk.Label(import_options, text="Number of columns:").grid(column=2, row=5)
            colHeader = tk.IntVar()
            colHeader.set(0)
            tk.Entry(import_options, textvariable=colHeader).grid(column=3, row=5)

            tk.Button(import_options, text="Compute data statistics",
                      command=partial(self.showRawDataDistributions, file_type='csv')).grid(column=1, row=7)

            # filter parameters
            filterCellMinVar = tk.StringVar()
            tk.Label(import_options, text="Filter by molecules per cell. Min:", fg="black", bg="white").grid(column=0,
                                                                                                              row=8)
            tk.Entry(import_options, textvariable=filterCellMinVar).grid(column=1, row=8)

            filterCellMaxVar = tk.StringVar()
            tk.Label(import_options, text=" Max:", fg="black", bg="white").grid(column=2, row=8)
            tk.Entry(import_options, textvariable=filterCellMaxVar).grid(column=3, row=8)

            filterGeneNonzeroVar = tk.StringVar()
            tk.Label(import_options, text="Filter by nonzero cells per gene. Min:", fg="black", bg="white").grid(
                     column=0, row=9)
            tk.Entry(import_options, textvariable=filterGeneNonzeroVar).grid(column=1, row=9)

            filterGeneMolsVar = tk.StringVar()
            tk.Label(import_options, text="Filter by molecules per gene. Min:", fg="black", bg="white").grid(column=0,
                                                                                                              row=10)
            tk.Entry(import_options, textvariable=filterGeneMolsVar).grid(column=1, row=10)

            # normalize
            normalizeVar = tk.BooleanVar()
            normalizeVar.set(True)
            tk.Checkbutton(import_options, text="Normalize by library size", variable=normalizeVar).grid(column=0,
                                                                                                         row=11)

            # log transform
            logTransform = tk.BooleanVar()
            logTransform.set(True)
            tk.Checkbutton(import_options, text="Log-transform data", variable=logTransform).grid(column=2, row=11)

            tk.Button(import_options, text="Cancel", command=import_options.destroy).grid(column=1, row=12)
            tk.Button(import_options, text="Load", command=partial(self.process_data, file_type='csv')).grid(column=2,
                                                                                                             row=12)

            # put MAGIC options here

            self.wait_window(import_options)

    def load_mtx(self):
        pass

    def load_10x(self):
        pass

    def load_pickle(self):
        pass

    def showRawDataDistributions(self):
        pass

    def process_data(self, file_type):
        pass

    def concatenate_data(self):
        pass

    def save_data(self):
        pass

    def save_plot(self):
        pass

    def run_dr(self):
        pass

    def run_clustering(self):
        pass

    def run_gea(self):
        pass

    def tsne(self):
        pass

    def scatter_plot(self):
        pass

    def quit_scras(self):
        pass


def launch():
    app = SCRASGui(None)
    if platform.system() == 'Darwin':
        app.focus_force()
    elif platform.system() == 'Windows':
        app.lift()
        app.call('wm', 'attributes', '.', '-topmost', True)
        app.after_idle(app.call, 'wm', 'attributes', '.', '-topmost', False)
    elif platform.system() == 'Linux':
        app.focus_force()

    app.title('SCRAS')

    while True:
        try:
            app.mainloop()
            break
        except UnicodeDecodeError:
            pass


if __name__ == "__main__":
    launch()