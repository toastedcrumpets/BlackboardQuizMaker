#!/usr/bin/env python

#An example way of parsing your own csv file format

import BlackboardQuiz
import csv
import sys
from random import shuffle

if len(sys.argv) < 3:
    print "Usage: csv_parser.py course_ID pool_1.csv [pool_2.csv ...]"
    print " output is in course_ID.zip"
    print "  Each line of pool_X.csv should have the following structure"
    print '  "Question", "Correct answer", "Incorrect answer 1","Incorrect answer 2",...'
    exit()

import os
with BlackboardQuiz.Package(sys.argv[1], useLaTeX=True) as package:
    for csv_file_name in sys.argv[2:]:
        if csv_file_name[-4:] != '.csv':
            raise Exception("File "+csv_file_name+" does not end in .csv!")

        pool_name = os.path.basename(csv_file_name)[:-4]
        with open(csv_file_name,'rb') as csvfile, package.createPool(pool_name) as pool:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)
            for row in reader:
                if len(row) == 0:
                    continue
            
                #Shuffle the answers
                answer_idxs = list(range(1, len(row)))
                shuffle(answer_idxs)
                answers = map(lambda x : row[x], answer_idxs)
                pool.addQuestion(row[0], answers, correct=answer_idxs.index(1)+1)
