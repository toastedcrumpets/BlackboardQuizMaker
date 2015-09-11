#!/usr/bin/env python

import BlackboardQuiz

with BlackboardQuiz.Quiz("Index notation questions") as quiz:
    quiz.addQuestion('What is the following in index notation?<br/> $\\vec{a}+\\vec{b}$', ['$a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'], correct=1)

    #Embedding external images is easy too
    img_tag = quiz.embed_image('example_image.png')    
    quiz.addQuestion('I cant believe that you can embed images!'+img_tag+' Cool huh?', ['Really cool', 'Well, its not that impressive, its basic functionality', 'Blackboard sucks'], correct=1)
