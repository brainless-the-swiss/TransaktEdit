import tkinter as tk
import pandas as pd
import os
import sys
from pathlib import Path

class SelectedData:
    def __init__ (self, column_names = None, rows_list = None, categories = None):
        '''List of lists of rows selected
        The point of this class is to make abstraction of the way rows are selected (from csv file, database or fake data)
        '''
        self.column_names = column_names    #name of each column header
        self.rows_list = rows_list          #list of lists of rows selected
        self.categories = categories

    def save (self, rowIndex, row):
        raise NotImplementedError() #On purpose, this is an interface

    def selectCategory (self, category, currentIndex):
        raise NotImplementedError() #On purpose, this is an interface

class FakeDataForTests (SelectedData):
    def __init__ (self):
        super ().__init__ ()
        self.column_names = ['id', 'transaction_date', 'description', 'amount', 'category_id', 'account_id']
        self.rows_list = [
            [1531, 2016, 'COMPER', -2190, 'Banco de Buenos Aires', 53],
            [1532, 2016, 'COMPER', -4300, 'Starbucks', 40],
            [1533, 2016, 'transaction', 20000, 'Le Parc restaurant', 19],
            [1534, 2017, 'payment', 200000, 'United Airlines', 987],
        ]
        self.categories = ['airline', 'banking transaction', 'restaurant/shop/convenience store', 'online shopping', 'cash withdrawal']

    def save (self, rowIndex, row):
        self.rows_list[rowIndex] = row

    def selectCategory (self, category, currentIndex):
        categoryIndex = self.column_names.index ('category_id')
        self.rows_list[currentIndex][categoryIndex] = category

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
        self.categories = ['airline', 'banking transaction', 'restaurant/shop/convenience store', 'online shopping', 'cash withdrawal']
    
    def save (self, rowIndex, row):
        self.rows_list[rowIndex] = row

        #Todo: save to csv file

    def selectCategory (self, category, currentIndex):
        categoryIndex = self.column_names.index ('category_id')
        self.rows_list[currentIndex][categoryIndex] = category

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
        self.widget = tk.Label (parent, text = value, font = 'Helvetica 8 bold')

class EditableCell (Cell):
    def __init__ (self, parent, value = None):
        super ().__init__ (parent, value)
        self.labelVar = tk.StringVar ()
        self.widgetOriginal = tk.Label (parent, textvariable = self.labelVar, justify = 'center')
        self.widgetOriginal.config (disabledforeground = "red", state = "disabled")
        self.widgetOriginal.grid (row = 2, column = 0, sticky = 'news')

    def edit (self, *args):
        if str (self.var.get ()) == str (self.oldValue):
            self.labelVar.set ('')
            self.widget.config (fg = 'black')
        else:
            self.labelVar.set (self.oldValue)
            self.widget.config (fg = 'green')

class SpreadSheet:
    def __init__(self, selected_data=FakeDataForTests()):
        self.selected_data = selected_data

        #Current row being edited in the data
        self.current_index = 0

        self.root = tk.Tk ()

        self.canvas = tk.Canvas (self.root, borderwidth = 0, background = '#ffffff', width = 1000)

        self.frameRoot = tk.Frame (self.canvas, background = '#ffffff')

        self.scrollH = tk.Scrollbar (self.root, orient = 'horizontal', command = self.canvas.xview)
        self.canvas.configure (xscrollcommand = self.scrollH.set)

        self.scrollH.pack (side = 'bottom', fill = 'x')
        self.canvas.create_window ((0, 0), window = self.frameRoot, anchor = 'nw')

        self.panedWindow = tk.PanedWindow(self.frameRoot)

        self.panedWindow.pack (expand = "yes", fill = tk.BOTH)
        self.panedWindow.configure (sashrelief = tk.RAISED)

        self.AddColumns ()

        self.AddPrevButton ()
        self.AddNextButton ()

        #Todo:
        #The width needs to exceed the sum of widths of each column (except the last empty column)
        #We need to use another number for this width...
        self.panedWindow.config (width = 2000)

        #self.frameRoot.update_idletasks ()
        self.frameRoot.bind ("<Configure>", lambda event, canvas = self.canvas: self.onFrameConfigure (self.canvas))

        self.canvas.pack (side = 'left', fill = 'both', expand = "yes")

    def AddColumns (self):
        nColumns = len (self.selected_data.column_names)
        self.editableCells = [None for i in range (nColumns)]

        for i in range (nColumns):
            self.editableCells[i] = editableCell = self.AddColumn (self.selected_data.column_names[i], self.selected_data.rows_list[0][i])
            if self.selected_data.column_names[i] == 'category_id':
                self.AddCategoryColumn (self.selected_data.categories, editableCell)

        #Add an empty column to make the right most sash resizeable interactively
        self.AddEmptyColumn (self.panedWindow)

    def AddColumn (self, headerText, firstRow):
        #Put the entire column in a frame
        frame = tk.Frame (self.panedWindow)
        frame.grid (column = 0, row = 0, sticky = 'news')
        frame.columnconfigure (0, weight = 1)
        frame.rowconfigure (1, weight = 1)

        self.panedWindow.add (frame, width = max (len (headerText), len (str (firstRow))) * 7 + 10)

        headerCell = HeaderCell (frame, headerText)
        editableCell = EditableCell (frame, firstRow)

        headerCell.widget.grid (row = 0, column = 0, sticky = 'news')
        editableCell.widget.grid (row = 1, column = 0, sticky = 'news')

        #Add empty cells in order to fill the empty space at the bottom of the column
        if headerText != 'candidate category ids':
            emptyCells = [tk.Label (frame) for i in range (max (0, len (self.selected_data.categories) - 1))]
            i = 3
            for emptyCell in emptyCells:
                emptyCell.grid (row = i, column = 0, sticky = 'news', rowspan = 1)
                i += 1

        return editableCell

    def AddEmptyColumn (self, panedWindow):
        frame = tk.Frame (panedWindow)
        panedWindow.add (frame, stretch = "always")

    def AddNextButton (self):
        curDir = os.path.dirname (os.path.realpath (sys.argv[0]))
        nextButtonPath = os.path.join (curDir, 'Button Next_256.png')
        self.nextImage = tk.PhotoImage (file = nextButtonPath).subsample (15, 15)
        nextButton = tk.Button (
            self.frameRoot,
            text = 'Save and Next ',
            image = self.nextImage,
            compound = tk.RIGHT,
            command = self.MoveToNext,
            pady = 10
            )
        nextButton.pack (side = tk.LEFT, anchor = 'w', pady = 10, padx = 10)

    def AddPrevButton (self):
        curDir = os.path.dirname (os.path.realpath (sys.argv[0]))
        prevButtonPath = os.path.join (curDir, 'Button Previous_256.png')
        self.prevImage = tk.PhotoImage (file = prevButtonPath).subsample (15, 15)
        nextButton = tk.Button (
            self.frameRoot,
            text = ' Save and Previous',
            image = self.prevImage,
            compound = tk.LEFT,
            command = self.MoveToPrev,
            pady = 10
            )
        nextButton.pack (side = tk.LEFT, anchor = 'w', pady = 10, padx = 10)

    def UpdateCells (self, row):
        i = 0
        for cell in self.editableCells:
            value = self.selected_data.rows_list[row][i]
            cell.var.set (value)
            cell.oldValue = value
            cell.labelVar.set (value)
            cell.edit ()
            i += 1

    def MoveToNext (self):
        #Save to the current data
        self.selected_data.save (self.current_index, [cell.var.get () for cell in self.editableCells])
        self.UpdateCells (self.current_index)

        #Move the index
        if self.current_index < len (self.selected_data.rows_list) - 1:
            self.current_index += 1
            self.UpdateCells (self.current_index)

    def MoveToPrev (self):
        #Save to the current data
        self.selected_data.save (self.current_index, [cell.var.get () for cell in self.editableCells])
        self.UpdateCells (self.current_index)

        #Move the index
        if self.current_index > 0:
            self.current_index -= 1
            self.UpdateCells (self.current_index)

    def SelectCategory (self, category, editableCell):
        self.currentCategory = category
        editableCell.var.set (category)
        self.selected_data.selectCategory (category, self.current_index)

    def AddCategoryColumn (self, categories, editableCell):
        frame = tk.Frame (self.panedWindow)
        frame.grid (column = 0, row = 0, sticky = 'news')
        frame.columnconfigure (0, weight = 1)
        frame.rowconfigure (1, weight = 1)

        headerCell = HeaderCell (frame, 'candidate category ids')
        headerCell.widget.grid (row = 0, column = 0, sticky = 'news')

        i = 1
        maxWidth = 10
        for category in categories:
            button = tk.Button (frame, text = category)
            button.grid (row = i, column = 0, sticky = 'news')
            button.configure (command = lambda category = button['text'], editableCell = editableCell : self.SelectCategory (category, editableCell))
            i += 1
            maxWidth = max (maxWidth, len (category) * 7 + 10)
        
        self.panedWindow.add (frame, width = maxWidth)

    def onFrameConfigure(self, canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=self.canvas.bbox("all"))

    def Run (self):
        self.root.mainloop ()

SpreadSheet (selected_data = DataFromCsv (Path ("C:/dev/python/trainBuf.csv"), lineStart = 100, nrows = 30)).Run ()
