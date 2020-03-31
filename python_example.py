#!/usr/bin/env python3

import BlackboardQuiz

#You need a package, which is what you'll eventually upload to
#Blackboard/MyAberdeen
with BlackboardQuiz.Package("MyQuestionPools") as package:

    #You may have multiple question pools in a single package, just
    #repeat this block with different pool names. This pool is just 
    with package.createPool('Unique questions', description="Questions which are not generated/calculated", instructions="") as pool:
        #We can do numerical questions
        pool.addNumQ('Douglas Adams Question', 'What is the answer to life, the universe, and everything?', 42, erramt=0.1, positive_feedback="Good, you have read well.", negative_feedback="Where have you been?")

        #Or multiple choice questions
        pool.addMCQ('Shakespeare','To be, or not to be', answers=["To be.", "Not to be.", "That is the question.", "Both."],  correct=2, positive_feedback="Again, you have read well.", negative_feedback="Try reading Hamlet.")

        #Maths can be included using latex
        pool.addMCQ('Math question', 'Please solve this "display" equation: $$\\int x\,dx=?$$',
                    answers=['$x$', '$\\frac{x^2}{2}$', '$gh$'],
                    correct=1,
                    positive_feedback="Well done!",
                    negative_feedback="Sorry, but the general rule for polynomial integration is $\\int x^n\\,dx=\\frac{x^{n+1}}{n+1}$ for $n\\neq -1$"
        )
        
        #Embedding external images is easy too and will automatically
        #be included into the package. Other HTML can also be used for
        #formatting, I don't check it.
        pool.addMCQ('HTML question', 'I cant believe that you can embed images! <img src="example_image.png"> Cool huh?',
                    ['Really cool.', 'Well, its not that impressive, its basic functionality.', 'Blackboard sucks.'],
                    correct=0)

    #Create a pool with 10 variations of the same simple linear equation to solve.
    with package.createPool('Linear function solving', description="Solve the $y=m*x+c$", instructions="") as pool:
        import random
        for i in range(10):
            m = round(random.uniform(-10, 10), 2) #2 d.p. random m in [-10,10]
            y = round(random.uniform(-42, 42), 2) #2 d.p. random m in [-42,42]
            c = round(random.uniform(-100, 100), 2) #2 d.p. random m in [-100,100]
            x = round((y-c)/m, 2) #The answer
            # Add this as a numerical question, with a 1% margin for error
            pool.addNumQ('Linear function solving', 'Determine $x$ for $'+repr(y)+'='+repr(m)+'x+'+repr(c)+'$', answer=x, errfrac=0.05)

    #Do the same as above, but using the calc question interface
    with package.createPool('Linear function solving2', description="Solve the $y=m*x+c$", instructions="") as pool:
        import scipy
        #First, declare the "random" variables
        xs = {
            'm' : [scipy.stats.uniform(-10, 10), 2], #2 S.F.
            'y' : [scipy.stats.uniform(-42, 42), 2],  #2 S.F.
            'c' : [[1.2, 3.4, 5.5], None] # A list of potential values
        }

        # Then declare a function that takes the particular values of
        # the random variables, calculates any other variables
        # including the answer. This is very powerful as you can use
        # ANY of the the variables in the question text.
        def calc(x):
            x['answer'] = (x['y']-x['c']) / x['m']
            x['roughanswer'] = BlackboardQuiz.roundSF(x['answer'], 1)
            return x
        
        pool.addCalcNumQ(
            title='Linear function solving',
            # Notice the placeholders for variables, i.e. [y]
            text=r'Determine $x$ for $[y]=[m]x +[c]$ (Hint the answer is roughly [roughanswer])', 
            xs=xs,
            calc = calc,
            count = 10, #Create 10 questions randomly
            errfrac = 0.05,
            # Can even use the variables in the feedback
            negative_feedback="Actually the answer was [answer]"
        )
        
    #One of the most interesting implementations, multi-part REGEX questions!
    with package.createPool('Regex questions', description="Unlimited regex power", instructions="") as pool:
        pool.addFITBQ(title="Crazy regex1", text=r'''How much [A] would a [B] chuck chuck if a [C] chuck could [D]
        wood?''',
                      answers={
                          'A':['wood'], #basic word matching
                          'B':['(WOOD|wood)'], # Match allcaps too
                          'C':[r'''w[o0]{2}d'''], # Allow leet speak (i.e. w00d or wo0d or w0od)
                          'D':['chuck', 'Chuck', 'CHUCK'], #Multiple matching patterns if needed
                      })

