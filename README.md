# BlackboardQuizMaker
A python module which lets you create multiple choice question pools with LaTeX math expressions as a zip package which you can import int Blackboard.
Even images can be included.

# Dependencies
This needs python, python-lxml, and python-matplotlib.

# How to use it via python
Simply create an instance of the quiz class using the "with" pattern, and add questions!
```python
import BlackboardQuiz

with BlackboardQuiz.Quiz("Index notation questions") as quiz:
    quiz.addQuestion(r'What is the following in index notation?<br/> $\vec{a}+\vec{b}$',
                     ['The correct answer is $a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'],
                     correct=1)
    #Note that answers are indexed from 1 to 3, not zero (so the
    #correct answer is the first one)

    #Also note that here we are using python raw strings (r'foo'),
    #which means we don't have to escape backslashes and can just type
    #latex directly in.
    
    #You can also set the feedback using positive_feedback and
    #negative_feedback which can also contain images or latex
    quiz.addQuestion(r'This is a display equation: $$\int x\,dx=?$$',
                     [r'$x$', r'$\frac{x^2}{2}$'],
                     correct=2,
                     positive_feedback="Well done!",
                     negative_feedback=r"Sorry, but the rule for integration is $\int x^n\,dx=\frac{x^{n+1}}{n+1}$ for $n\neq -1$"
    )
    
    #Embedding external images is easy too
    img_tag = quiz.embed_image('example_image.png')    
    quiz.addQuestion('I cant believe that you can embed images!'+img_tag+' Cool huh?',
                     ['Really cool', 'Well, its not that impressive, its basic functionality', 'Blackboard sucks'],
                     correct=1)
```
Note, you can embed html in the questions as well, to give you line breaks or other formatting. You can even embed external images if you want to.
# How to use it via a csv file

To be honest, the python interface is a bit clunky. I'd like to just
write all the questions into a file and have a tool to convert this
file, which is really simple to make using the python interface. Taking a look at csv_reader.py:
```python
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
```
Now I can just make a file MyQuiz.csv which contains:
```
"Convert $\vec{a}+\vec{b}$ to index notation.", "$a_k+b_k$", "$a_i+a_i$", "$a_i+b_j$"
```

Then run ./csv_reader.py MyQuiz.csv will give me MyQuiz.zip with all
the rendered latex formula included!

# How it works
Blackboard has an XML file format which it uses to upload/download question sets or "pools". This file format lets you also send images and this is how the LaTeX support is implemented. All strings are searched for $$ which indicate a LaTeX string, then these are rendered using Matplotlib. The resulting png images are then embedded in the zip and the $$ tags are replaced by links to these images.

This was figured out by reverse engineering their file format, and the question generator here: http://www.csi.edu/blackboard/bbquiz/
