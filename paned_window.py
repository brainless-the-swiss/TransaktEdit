import tkinter as tk
from tkinter import messagebox
import pandas as pd
import numpy as np
import os
import sys
import json
import sqlite3
from sqlite3 import Error
from pathlib import Path

class SelectedData:
    def __init__ (self, column_names = None, rows_list = None, categories = None, categoriesGUI = None):
        '''List of lists of rows selected
        The point of this class is to make abstraction of the way rows are selected (from csv file, database or fake data)
        '''
        self.column_names = column_names    #name of each column header
        self.rows_list = rows_list          #list of lists of rows selected
        self.categories = categories        #categories to select
        self.categoriesGUI = categoriesGUI  #categories to be displayed in the GUI (e.g. '[parent category] - [category]')

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
        self.categoriesGUI = ['shopping', 'transfers', 'food']

    def save (self, rowIndex, row):
        self.rows_list[rowIndex] = row

    def selectCategory (self, category, currentIndex):
        categoryIndex = self.column_names.index ('category_id')
        self.rows_list[currentIndex][categoryIndex] = category

class SqliteFile:
    def filename (self):
        raise NotImplementedError

class SqliteDefaultFile (SqliteFile):
    def filename (self):
        filePath = \
            self.__joinedDir (
                self.__joinedDir (
                    os.environ ['APPDATA'],
                    'ubank'
                ),
                'dataEditing'
            )
        fullPath = os.path.join (filePath, 'transactions.db')
        os.remove (fullPath)
        return fullPath

    def __joinedDir (self, baseFolder, appended):
        folderName = os.path.join (baseFolder, appended)
        if not os.path.isdir (folderName):
            os.mkdir (folderName)
        return folderName
    
class SqliteMemoryFile (SqliteFile):
    def filename (self):
        return ":memory:"

class SqliteData:
    def __init__ (self, filename = SqliteDefaultFile ()):
        self.filename = filename
        self.connection = None
        try:
            self.connection = sqlite3.connect (self.filename.filename ())
        except Error as e:
            print (e)

    def close (self):
        if self.connection:
            self.connection.close ()

    def __createTable (self, create_table_sql):
        try:
            c = self.connection.cursor()
            c.execute (create_table_sql)
        except Error as e:
            print (e)

    def __createCategoriesTable (self):
        sql_create_table = """ CREATE TABLE IF NOT EXISTS categories (
                               id integer PRIMARY KEY,
                               category text NOT NULL
                            ); """
        self.__createTable (sql_create_table)

    def __createTransactionsTable (self):
        sql_create_table = """  CREATE TABLE IF NOT EXISTS transactions (
                                id integer PRIMARY KEY,
                                transaction_id integer NOT NULL,
                                category text NOT NULL
                            );"""
        self.__createTable (sql_create_table)

    def __saveCategories (self, categories):
        self.__createCategoriesTable ()
        cur = self.connection.cursor ()
        for category in categories:
            sql = ''' INSERT INTO categories (category) VALUES (?)'''
            cur.execute (sql, (category,))

    def __saveTransactions (self, rows_list, column_names):
        self.__createTransactionsTable ()
        categoryIndex = column_names.index ("category_id")
        for row in rows_list:
            sql = ''' INSERT INTO transactions (transaction_id, category) VALUES (?, ?)'''
            cur = self.connection.cursor ()
            cur.execute (sql, (row[0], row[categoryIndex]))

    def save (self, selectedData):
        self.__saveCategories (selectedData.categories)
        self.__saveTransactions (selectedData.rows_list, selectedData.column_names)

    def update (self, transactionId, category):
        sql = ''' UPDATE transactions SET category = ? WHERE transaction_id = ? '''
        cur = self.connection.cursor ()
        cur.execute (sql, (category, transactionId))

    def selectTransaction (self, transactionId):
        cur = self.connection.cursor()
        cur.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transactionId,))
        result = cur.fetchall ()
        return result[0]

class PathsFromJson:
    def __loadedJsonValue (self):
        curDir = os.path.dirname (os.path.realpath (sys.argv[0]))
        pathsFile = os.path.join (curDir, 'paths.json')
        jsonFile = open (pathsFile)
        return json.load (jsonFile)

    def dataPath (self):
        return Path (self.__loadedJsonValue ()['data'])

    def categoriesPath (self):
        return Path (self.__loadedJsonValue ()['categories'])

    def outputCsvPath (self):
        return Path (self.__loadedJsonValue ()['outputCsv'])

class DataFromCsv (SelectedData):
    def __init__ (self, lineStart = 0, nrows = None):
        '''Select data from a csv file
        path: full path to csv file, expected type Path from pathlib (because it's cross platform)
        lineStart: first line to select
        nrows: numner of rows to select
        '''
        super ().__init__ ()
        self.pathsFromJson = PathsFromJson ()
        self.path = self.pathsFromJson.dataPath ()
        self.categoriesPath = Path (os.path.join (os.path.dirname (os.path.realpath (sys.argv[0])), 'categories_tree_with_english.csv'))
        self.lineStart = lineStart
        self.nrows = nrows
        assert lineStart >= 0
        if nrows:
            assert nrows >= 0
        assert self.path.is_file ()
        assert self.categoriesPath.is_file ()

        #self.db = SqliteData ()
        self.select ()

    def select (self):
        self.selectData ()
        self.selectCategories ()
        self.mapCategories ()
        #self.db.save (self)
        
    def selectData (self):
        data = pd.read_csv (
            self.path,
            sep = ';',
            engine = 'python',
            skipinitialspace = True,
            skiprows = range (1, max (self.lineStart - 1, 0)),
            nrows = self.nrows if self.nrows else None,
            )

        self.column_names = data.columns.to_numpy ().tolist ()
        categoryIndex = self.column_names.index ('category_id')
        descrIndex = self.column_names.index ('description')
        self.column_names[0], self.column_names[descrIndex] = self.column_names[descrIndex], self.column_names[0]
        self.column_names[1], self.column_names[categoryIndex] = self.column_names[categoryIndex], self.column_names[1]

        data = data[self.column_names]
        self.rows_list = data.to_numpy ().tolist ()

    def selectCategories (self):
        self.rawCategories = pd.read_csv (
            self.categoriesPath,
            sep = ',',
            engine = 'python',
            skipinitialspace = True,
        )
        dfCategories = self.rawCategories.loc[:, 'category_descr_english']
        self.categories = dfCategories.to_numpy ().tolist ()
        dfParentCat = self.rawCategories.loc[:, 'parent_category_descr_english']
        parentCategories = dfParentCat.to_numpy ().tolist ()

        mapping = list (zip (self.categories, parentCategories))
        self.categoriesGUI = ['[' + parent + '] - ' + category for category, parent in mapping]

    def mapCategories (self):
        dfcatIds = self.rawCategories.loc[:, 'category_id']
        catIds = dfcatIds.to_numpy ().tolist ()
        mapping = dict (zip (catIds, self.categories))
        for i in range (len (self.rows_list)):
            if self.rows_list[i][1] in mapping:
                self.rows_list[i][1] = mapping[self.rows_list[i][1]]

    def __categoryIndex (self):
        return self.column_names.index ('category_id')

    def save (self, rowIndex, row):
        self.rows_list[rowIndex] = row

        #Update the db
        #self.db.update (row[0], row[self.__categoryIndex ()])

    def selectCategory (self, category, currentIndex):
        self.rows_list[currentIndex][self.__categoryIndex ()] = category

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

    def display (self):
        raise NotImplementedError ()

class HeaderCell (Cell):
    def __init__ (self, parent, value = None):
        self.widget = tk.Label (parent, text = value, font = 'Helvetica 8 bold')

    def display (self):
        self.widget.pack ()

class EditableCell (Cell):
    def __init__ (self, parent, value = None):
        super ().__init__ (parent, value)
        self.labelVar = tk.StringVar ()
        self.widgetOriginal = tk.Label (parent, textvariable = self.labelVar, justify = 'center')
        self.widgetOriginal.config (disabledforeground = "red", state = "disabled")

    def edit (self, *args):
        if str (self.var.get ()) == str (self.oldValue):
            self.labelVar.set ('')
            self.widget.config (fg = 'black')
        else:
            self.labelVar.set (self.oldValue)
            self.widget.config (fg = 'green')

    def display (self):
        self.widget.pack (expand = True, fill = tk.BOTH)
        self.widgetOriginal.pack ()

class SpreadSheet:
    def __init__(self, selected_data=FakeDataForTests()):
        self.selected_data = selected_data

        #Current row being edited in the data
        self.current_index = 0

        self.root = tk.Tk ()

        self.canvas = tk.Canvas (self.root, borderwidth = 0, background = '#ffffff', width = 1000, height = 600)

        self.frameRoot = tk.Frame (self.canvas, background = '#ffffff')

        self.scrollH = tk.Scrollbar (self.root, orient = 'horizontal', command = self.canvas.xview)
        self.scrollV = tk.Scrollbar (self.root, orient = 'vertical', command = self.canvas.yview)
        self.canvas.configure (xscrollcommand = self.scrollH.set, yscrollcommand = self.scrollV.set)
        self.canvas.bind_all ('<MouseWheel>', self._on_mousewheel)

        self.scrollH.pack (side = 'bottom', fill = 'x')
        self.scrollV.pack (side = 'left', fill = 'y')
        self.canvas.create_window ((0, 0), window = self.frameRoot, anchor = 'nw')

        self.panedWindow = tk.PanedWindow(self.frameRoot)

        self.panedWindow.pack (expand = "yes", fill = tk.BOTH)
        self.panedWindow.configure (sashrelief = tk.RAISED)

        self.AddColumns ()

        self.AddPrevButton ()
        self.AddNextButton ()
        self.AddSaveToCsvButton ()

        #Todo:
        #The width needs to exceed the sum of widths of each column (except the last empty column)
        #We need to use another number for this width...
        self.panedWindow.config (width = 4000)

        #self.frameRoot.update_idletasks ()
        self.frameRoot.bind ("<Configure>", lambda event, canvas = self.canvas: self.onFrameConfigure (self.canvas))

        self.canvas.pack (side = 'left', fill = 'both', expand = "yes")

        self.pathsFromJson = PathsFromJson ()
        self.outputPath = self.pathsFromJson.outputCsvPath ()

    def AddColumns (self):
        nColumns = len (self.selected_data.column_names)
        self.editableCells = [None for i in range (nColumns)]

        for i in range (nColumns):
            self.editableCells[i] = editableCell = self.AddColumn (self.selected_data.column_names[i], self.selected_data.rows_list[0][i])
            if self.selected_data.column_names[i] == 'category_id':
                self.AddCategoryColumn (self.selected_data.categories, self.selected_data.categoriesGUI, editableCell)

        #Add an empty column to make the right most sash resizeable interactively
        self.AddEmptyColumn (self.panedWindow)

    def AddColumn (self, headerText, firstRow):
        #Put the entire column in a frame
        frame = tk.Frame (self.panedWindow)
        frame.pack (anchor = 'n', fill = tk.BOTH, expand = False, side = tk.TOP)

        minWidth = 30
        txtLen = max (len (headerText), len (str (firstRow))) * 7 + 10
        width = max (minWidth, txtLen)

        self.panedWindow.add (frame, sticky = 'new', minsize = width)

        headerCell = HeaderCell (frame, headerText)
        editableCell = EditableCell (frame, firstRow)

        headerCell.display ()
        editableCell.display ()

        #Add empty cells in order to fill the empty space at the bottom of the column
        emptyCell = tk.Label (frame)
        emptyCell.pack ()

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

        self.root.bind ('<Right>', self.MoveToNext)

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

        self.root.bind ('<Left>', self.MoveToPrev)

    def AddSaveToCsvButton (self):
        curDir = os.path.dirname (os.path.realpath (sys.argv[0]))
        buttonPath = os.path.join (curDir, 'Button_save_as_csv.png')
        self.saveCsvImage = tk.PhotoImage (file = buttonPath).subsample (3, 3)
        nextButton = tk.Button (
            self.frameRoot,
            text = 'Save to CSV file ',
            image = self.saveCsvImage,
            compound = tk.RIGHT,
            command = self.SaveToCsv,
            pady = 10
            )
        nextButton.pack (side = tk.BOTTOM, anchor = 'w', pady = 10, padx = 10)

        self.root.protocol ("WM_DELETE_WINDOW", self.onClosing)

    def UpdateCells (self, row):
        i = 0
        for cell in self.editableCells:
            value = self.selected_data.rows_list[row][i]
            cell.var.set (value)
            cell.oldValue = value
            cell.labelVar.set (value)
            cell.edit ()
            i += 1

    def SaveFromUI (self):
        self.selected_data.save (self.current_index, [cell.var.get () for cell in self.editableCells])

    def MoveToNext (self, event = None):
        #Save to the current data from the UI
        self.SaveFromUI ()

        #Move the index
        if self.current_index < len (self.selected_data.rows_list) - 1:
            self.current_index += 1

        #Update the UI
        self.UpdateCells (self.current_index)

    def MoveToPrev (self, event = None):
        #Save to the current data from the UI
        self.SaveFromUI ()

        #Move the index
        if self.current_index > 0:
            self.current_index -= 1
            
        #Update the UI
        self.UpdateCells (self.current_index)

    def SelectCategory (self, category, editableCell):
        self.currentCategory = category
        editableCell.var.set (category)
        #self.selected_data.selectCategory (category, self.current_index)

    def AddCategoryColumn (self, categories, categoriesGUI, editableCell):
        frame = tk.Frame (self.panedWindow)
        frame.pack (anchor = 'n', fill = tk.BOTH, expand = True, side = tk.TOP)
    
        headerCell = HeaderCell (frame, 'candidate category ids')
        headerCell.widget.pack (fill = tk.BOTH, expand = False, side = tk.TOP)

        maxWidth = 10
        for category, catGUI in list (zip (categories, categoriesGUI)):
            button = tk.Button (frame, text = catGUI, anchor = 'n')
            button.pack (fill = tk.BOTH, expand = False, side = tk.TOP)
            button.configure (command = lambda category = category, editableCell = editableCell : self.SelectCategory (category, editableCell))
            maxWidth = max (maxWidth, len (category) * 7 + 10)
        
        self.panedWindow.add (frame, minsize = maxWidth)

    def SaveToCsv (self):
        self.SaveFromUI ()
        df = pd.DataFrame (np.array (self.selected_data.rows_list), columns = self.selected_data.column_names)
        df.to_csv (self.outputPath)

        #Update the UI
        self.UpdateCells (self.current_index)

        messagebox.showinfo ("Saved to CSV", "Saved to CSV")

    def onClosing (self):
        confirm = messagebox.askyesnocancel ("Quit", "Save to CSV before quitting?")
        if confirm: #yes
            self.SaveToCsv ()
            self.root.destroy ()
        elif confirm is None: #cancel
            return
        else: #no
            self.root.destroy ()

    def onFrameConfigure(self, canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel (self, event):
        self.canvas.yview_scroll(int (- event.delta / 120), "units")

    def Run (self):
        self.root.mainloop ()

if __name__ == '__main__':
    SpreadSheet (selected_data = DataFromCsv ()).Run ()

### Unit tests ###
import unittest
class Tests (unittest.TestCase):
    def testSqliteUpdate (self):
        db = SqliteData (filename = SqliteMemoryFile ())
        data = FakeDataForTests ()
        
        db.save (data)
        transactionId = data.rows_list[0][0]
        selectedCategory = data.categories[2]
        db.update (transactionId, selectedCategory)
        
        actualCategory = db.selectTransaction (transactionId)[2]
        db.close ()

        self.assertEqual (actualCategory, selectedCategory)

    #Todo: test that pressing "next" and "prev" buttons effectively saves to the db
