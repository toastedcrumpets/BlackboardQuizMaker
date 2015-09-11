#!/usr/bin/env python

#An example way of parsing your own csv file format

import BlackboardQuiz
import csv
import sys

if len(sys.argv) != 2:
    print "Usage: csv_parser.py TestName.csv"
    print " output is in TestName.zip"
    print "  Each line of TestName.csv should have the following structure"
    print '  "Question", "Correct answer", "Incorrect answer 1","Incorrect answer 2",...'
    exit()    

with BlackboardQuiz.Quiz(sys.argv[1][:-4]) as quiz:
    with open(sys.argv[1],'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)
        for row in reader:
            print row
            quiz.addQuestion(row[0], row[1:], correct=1)
