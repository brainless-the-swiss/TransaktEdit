import tkinter as tk
import pandas as pd
import os
import sys
import json
import sqlite3
from sqlite3 import Error
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

class DataFromCsv (SelectedData):
    def __init__ (self, lineStart = 0, nrows = 10, maxrows = 100):
        '''Select data from a csv file
        path: full path to csv file, expected type Path from pathlib (because it's cross platform)
        lineStart: first line to select
        nrows: numner of rows to select
        maxrows: maximum number of rows allowed for selection
        '''
        super ().__init__ ()
        self.path = self.pathFromJson ()
        self.categoriesPath = self.categoriesFromJson ()
        self.lineStart = lineStart
        self.nrows = nrows
        self.maxrows = maxrows
        assert lineStart >= 0 and nrows >= 0 and maxrows >= 0
        assert self.path.is_file ()

        self.select ()

    def loadedJsonValue (self):
        curDir = os.path.dirname (os.path.realpath (sys.argv[0]))
        pathsFile = os.path.join (curDir, 'paths.json')
        jsonFile = open (pathsFile)
        return json.load (jsonFile)

    def pathFromJson (self):
        return Path (self.loadedJsonValue ()['data'])

    def categoriesFromJson (self):
        return Path (self.loadedJsonValue ()['categories'])

    def select (self):
        self.selectData ()
        self.selectCategories ()
        
    def selectData (self):
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

    def selectCategories (self):
        categories = pd.read_csv (
            self.categoriesPath,
            sep = ',',
            engine = 'python',
            skipinitialspace = True,
        )
        #self.categories = ['airline', 'banking transaction', 'restaurant/shop/convenience store', 'online shopping', 'cash withdrawal']
        dfCategories = categories.loc[:, ['category_descr']]
        self.categories = dfCategories.to_numpy ().tolist ()

    def save (self, rowIndex, row):
        self.rows_list[rowIndex] = row

        #Todo: save to csv file

    def selectCategory (self, category, currentIndex):
        categoryIndex = self.column_names.get_loc ('category_id')
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
        self.panedWindow.config (width = 4000)

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
            button = tk.Button (frame, text = category, anchor = 'n')
            button.grid (row = i, column = 0, sticky = 'news')
            button.configure (command = lambda category = button['text'], editableCell = editableCell : self.SelectCategory (category, editableCell))
            i += 1
            maxWidth = max (maxWidth, len (category) * 7 + 10)
        
        self.panedWindow.add (frame, minsize = maxWidth)

    def onFrameConfigure(self, canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=self.canvas.bbox("all"))

    def Run (self):
        self.root.mainloop ()

if __name__ == '__main__':
    SpreadSheet (selected_data = DataFromCsv (lineStart = 100, nrows = 30)).Run ()

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
