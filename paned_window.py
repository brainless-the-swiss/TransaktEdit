import pandas as pd
import tkinter as tk

class SelectedData:
    def __init__ (self, column_names = None, rows_list = None, categories = None):
        '''List of lists of rows selected
        The point of this class is to make abstraction of the way rows are selected (from csv file, database or fake data)
        '''
        self.column_names = column_names    #name of each column header
        self.rows_list = rows_list          #list of lists of rows selected
        self.categories = categories

    def save (self):
        raise NotImplementedError() #On purpose, this is an interface

class FakeDataForTests (SelectedData):
    def __init__ (self):
        super ().__init__ ()
        self.column_names = ['id', 'transaction_date', 'description', 'amount', 'category']
        self.rows_list = [
            [1531, 2016, 'COMPRA', -2190, 'banco de Buenos Aires'],
            [1532, 2016, 'COMPRA', -4300, 'Starbucks'],
            [1533, 2016, 'Transf', 20000, 'Le Parc restaurant']
        ]
        self.categories = ['airline', 'banking transaction', 'restaurant/shop/convenience store']

    def save (self):
        pass #Empty on purpose

class DataFromCsv (SelectedData):
    def __init__ (self, path, lineStart = 0, nrows = 10, maxrows = 100):
        '''Select data from a csv file
        path: full path to csv file, expected type Path from pathlib (because it's cross platform)
        lineStart: first line to select
        nrows: numner of rows to select
        maxrows: maximum number of rows allowed for selection
        '''
        super ().__init__ ()
        self.path = path
        self.lineStart = lineStart
        self.nrows = nrows
        self.maxrows = maxrows
        assert lineStart >= 0 and nrows >= 0 and maxrows >= 0
        assert path.is_file ()

        self.select ()

    def select (self):
        data = pd.read_csv (
            self.path,
            sep = ';',
            engine = 'python',
            skipinitialspace = True,
            skiprows = range (1, max (self.lineStart - 1, 0)),
            nrows = min (self.nrows, self.maxrows),
            )
        self.rows_list = data.to_numpy ().tolist ()
        self.column_names = data.columns

    def save (self):
        raise NotImplementedError ()

class Cell:
    def __init__ (self, parent, value = None):
        self.var = tk.StringVar ()
        self.widget = tk.Entry (parent, textvariable = self.var, justify = 'center')
        self.oldValue = None
        if value:
            valueStr = str (value)
            self.var.set (valueStr)
            self.oldValue = valueStr
        self.var.trace_add ('write', self.edit)

    def edit (self, *args):
        raise NotImplementedError ()

class HeaderCell (Cell):
    def __init__ (self, parent, value = None):
        self.widget = tk.Label (parent, text = value)
        #self.widget.grid (row = 1, column = 0)

class EditableCell (Cell):
    def __init__ (self, widgetBelow, parent, value = None):
        super ().__init__ (parent, value)
        self.widgetBelow = widgetBelow

    def edit (self, *args):
        if self.var.get () == self.oldValue:
            self.widgetBelow.grid_remove ()
            self.widget.config (fg = 'black')
        else:
            self.widgetBelow.grid (row = 2, column = 0, sticky = 'sew')
            self.widget.config (fg = 'green')

class VersionedCell (Cell):
    def __init__ (self, parent, value = None):
        super ().__init__ (parent, value)
        #self.widget.grid (row = 3, column = 0)
        self.widget.config (disabledforeground = "red", state = "disabled")

    def edit (self, *args):
        pass #Do nothing on purpose

class SpreadSheet:
    def __init__(self, selected_data=FakeDataForTests()):
        self.root = tk.Tk ()

        self.canvas = tk.Canvas (self.root, borderwidth = 0, background = '#ffffff')

        self.frameRoot = tk.Frame (self.canvas, background = '#ffffff')

        #self.scrollV = tk.Scrollbar (self.root, orient = 'vertical', command = self.canvas.yview)
        self.scrollH = tk.Scrollbar (self.root, orient = 'horizontal', command = self.canvas.xview)
        self.canvas.configure (xscrollcommand = self.scrollH.set)#, yscrollcommand = self.scrollV.set)

        self.scrollH.pack (side = 'bottom', fill = 'x')
        #self.scrollV.pack (side = 'right', fill = 'y')
        self.canvas.create_window ((0, 0), window = self.frameRoot, anchor = 'nw')

        self.panedWindow = tk.PanedWindow(self.frameRoot)

        self.panedWindow.pack (expand = "yes", fill = tk.BOTH)
        self.panedWindow.configure (sashrelief = tk.RAISED)

        for i in range (0, len (selected_data.column_names)):
            self.AddColumn (selected_data.column_names[i], selected_data.rows_list[0][i])

        self.AddEmptyColumn (self.panedWindow)

        #Todo:
        #The width needs to exceed the sum of widths of each column (except the last empty column)
        self.panedWindow.config (width = 2000)

        #frameRoot.update_idletasks ()
        self.frameRoot.bind ("<Configure>", lambda event, canvas = self.canvas: self.onFrameConfigure (self.canvas))

        self.canvas.pack (side = 'left', fill = 'both', expand = "yes")

    def AddColumn (self, headerText, firstRow):
        #Put the entire column in a frame
        frame = tk.Frame (self.panedWindow)
        frame.grid (column = 0, row = 0)
        #frame.rowconfigure (0, weight = 1)
        #frame.columnconfigure (0, weight = 1)

        self.headerCell = HeaderCell (frame, headerText)
        self.versionnedCell = VersionedCell (frame, firstRow)
        self.editableCell = EditableCell (self.versionnedCell.widget, frame, firstRow)

        self.panedWindow.add (frame, width = max (len (headerText), len (str (firstRow))) * 7 + 10)

        self.headerCell.widget.grid (row = 0, column = 0, sticky = 'new')
        self.editableCell.widget.grid (row = 1, column = 0, sticky = 'new')
        #self.versionnedCell.widget.grid (row = 2, column = 0, sticky = 'ew')

    def AddEmptyColumn (self, panedWindow):
        frame = tk.Frame (panedWindow)
        #frame.grid (column = 0, row = 0)
        #frame.rowconfigure (0, weight = 1)
        #frame.columnconfigure (0, weight = 1)

        panedWindow.add (frame, stretch = "always")

    def onFrameConfigure(self, canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=self.canvas.bbox("all"))

    def Run (self):
        self.root.mainloop ()

SpreadSheet ().Run ()
