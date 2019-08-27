# Transaction labelling

## What it is and how to use it

This python program allows you to quickly categorize financial transactions.

To use it, start by editing the paths.json file:
 - "data": full path name to the csv file containing the transactions data
 - "outputCsv": full path name to the output csv

Now you're ready to run it.
This is in python 3, and was tested on Windows 10.

## Instructions to get the source code on your local machine (in case you're not familiar with github):
 - Clone this repository using git:
  * Install git (you may need to restart your computer after installation) : https://git-scm.com/download/win
  * Using the terminal, navigate to the folder in which you want to clone the source code (cf https://www.digitalcitizen.life/command-prompt-how-use-basic-commands)
  * In the terminal, run the key-in "git clone https://github.com/jpweng/TransaktEdit"
 - To pull the latest version to your local machine, navigate to the folder that contains this code on your machine, and enter "git pull"

## Unit tests

Unit tests can be run using the command "python -m unittest paned_window.py". Feel free to add more tests.

## Future developments

This is currently only a first iteration.
Please send me any remarks/comments so that I can enhance it iteratively.
There are multiple things to improve for a better usability...
Feel free to edit it yourself.

One suggestion would be to make this program directly edit data in a database instead of CSV files.
