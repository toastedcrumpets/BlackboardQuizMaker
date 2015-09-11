#!/usr/bin/env python

import BlackboardQuiz

with BlackboardQuiz.Quiz("Index notation questions") as quiz:
    quiz.addQuestion('What is the following in index notation?<br/> $\\vec{a}+\\vec{b}$', ['$a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'], 1)
