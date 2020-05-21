#!/usr/bin/env python3

from lxml import etree
import lxml.html as html
import time
import zipfile
import re
import os
import uuid
from xml.sax.saxutils import escape, unescape
from PIL import Image
from io import StringIO
from io import BytesIO
import itertools
import scipy.stats
import sympy
import random

def roundSF(val, sf):
    return float('{:.{p}g}'.format(val, p=sf))

def regexSF(val, sf):
    #This is not really functional. It will match floats but not with rounding restrictions!
    #Match the start of the string and any initial whitespace
    regex="^[ ]*" 

    #Match the sign of the variable
    if val < 0:
        regex = regex +'-' #negative is required
    else:
        regex = regex +'\+?' #plus is optional

    #Round the figure to the required S.F.
    val = str(roundSF(abs(val), sf))
    
    didx=val.find('.')
    if didx == -1:
        didx = len(val)
    
    if val[0]=='0':
        regex += re.search('(0\.[0]*[0-9]{0,'+str(sf)+'})', val).group(0) + "[0-9]*[ ]*"
    elif didx>=sf:
        regex += val[:sf]+"[0-9]{"+str(didx-sf)+'}(.|($|[ ]+))'
    else:
        regex += val[:sf+1].replace('.', r'\.')
    return regex
    

import subprocess
dn = os.path.dirname(os.path.realpath(__file__))
def render_latex(formula, display, *args, **kwargs):
    """Renders LaTeX expression to bitmap image data.
    """

    # Set a default math environment to have amsmath
    if 'preamble' not in kwargs:
        kwargs['preamble'] = r"""\documentclass[varwidth]{standalone}
        \usepackage{amsmath,amsfonts}
        \begin{document}"""

    if display:
        sympy.preview(r'\begin{align*}'+formula+r'\end{align*}', viewer='file', filename="out.png", euler=False, *args, **kwargs)
    else:
        sympy.preview('$'+formula+'$', viewer='file', filename="out.png", euler=False, *args, **kwargs)
        
    with open('out.png', 'rb') as f:
        data = f.read()
        
    im = Image.open(BytesIO(data))
    width, height = im.size
    del im
    return data, width, height

class Pool:
    def __init__(self, pool_name, package, description="Created by BlackboardQuiz!", instructions="", preview=True):
        """Initialises a question pool
        """
        self.package = package
        self.pool_name = pool_name
        self.preview = preview
        self.question_counter = 0
        
        #Create the question data file
        self.questestinterop = etree.Element("questestinterop")
        assessment = etree.SubElement(self.questestinterop, 'assessment', {'title':self.pool_name})

        md = etree.SubElement(assessment, 'assessmentmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Assessment'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Multiple Choice'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', ''),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        rubric = etree.SubElement(assessment, 'rubric', {'view':'All'})
        flow_mat = etree.SubElement(rubric, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, instructions)

        presentation_material = etree.SubElement(assessment, 'presentation_material')
        flow_mat = etree.SubElement(presentation_material, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, description)

        self.section = etree.SubElement(assessment, 'section')
        md = etree.SubElement(self.section, 'sectionmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Section'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Multiple Choice'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', ''),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        #Create the HTML file for preview
        self.htmlfile = "<html><head><style>li.correct, li.incorrect{list-style-type:none;} li.correct:before{content:'\\2713\\0020'}\nli.incorrect:before{content:'\\2718\\0020'}</style></head><body><p>Questions<ol>"

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.preview:
            self.package.zf.writestr(self.pool_name+'_preview.html', self.htmlfile+'</ol></body></html>')
        self.package.embed_resource(self.pool_name, "assessment/x-bb-qti-pool", '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(self.questestinterop, pretty_print=False).decode('utf-8'))
        
    def addNumQ(self, title, text, answer, errfrac=None, erramt=None, errlow=None, errhigh=None, positive_feedback="Good work", negative_feedback="That's not correct"):
        if errfrac is None and erramt is None and (errlow is None or errhigh is None):
            raise Exception("Numerical questions require an error amount, fraction, or bounds")
        if errfrac != None:
            #Min max are required here as some questions may have negative answers
            errlow = min(answer * (1-errfrac), answer * (1+errfrac))
            errhigh = max(answer * (1-errfrac), answer * (1+errfrac))
        if erramt != None:
            errlow = answer - abs(erramt)
            errhigh = answer + abs(erramt)
        
        self.question_counter += 1
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})

        md = etree.SubElement(item, 'itemmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Item'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Numeric'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', 'false'),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '-1.0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})

        bb_question_text, html_question_text = self.package.process_string(text)
        self.htmlfile += '<li>'+html_question_text+'<ul>'
        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        response_num = etree.SubElement(flow2, 'response_num', {'ident':'response', 'rcardinality':'Single', 'rtiming':'No'})
        etree.SubElement(response_num, 'render_fib', {'charset':'us-ascii', 'encoding':'UTF_8', 'rows':'0', 'columns':'0', 'maxchars':'0', 'prompt':'Box', 'fibtype':'Decimal', 'minnumber':'0', 'maxnumber':'0'})

        
        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':uuid.uuid4().hex})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'vargte', {'respident':'response'}).text = repr(errlow)
        etree.SubElement(conditionvar, 'varlte', {'respident':'response'}).text = repr(errhigh)
        etree.SubElement(conditionvar, 'varequal', {'respident':'response', 'case':'No'}).text = repr(answer)
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.flow_mat2(itemfeedback, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.flow_mat2(itemfeedback, bb_neg_feedback_text)
        
        self.htmlfile += '<li class="correct"><b>'+repr(errlow)+' &le; Answer &le; '+repr(errhigh)+'</b>:'+html_pos_feedback_text+'</li>'
        self.htmlfile += '<li class="incorrect"><b>Else</b>:'+html_neg_feedback_text+'</li>'
        self.htmlfile += '</ul></li>'
        print("Added NumQ "+repr(title))
        
    def addMCQ(self, title, text, answers, correct=0, positive_feedback="Good work", negative_feedback="That's not correct", shuffle_ans=True):
        
        self.question_counter += 1 
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
        md = etree.SubElement(item, 'itemmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Item'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Multiple Choice'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', 'false'),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '10.000000000000000'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})

        bb_question_text, html_question_text = self.package.process_string(text)
        self.htmlfile += '<li>'+html_question_text+'<ul>'
        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        response_lid = etree.SubElement(flow2, 'response_lid', {'ident':'response', 'rcardinality':'Single', 'rtiming':'No'})
        render_choice = etree.SubElement(response_lid, 'render_choice', {'shuffle':'Yes' if shuffle_ans else 'No', 'minnumber':'0', 'maxnumber':'0'})

        a_uuids = []
        for idx,text in enumerate(answers):
            flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
            a_uuids.append(uuid.uuid4().hex)
            response_label = etree.SubElement(flow_label, 'response_label', {'ident':a_uuids[-1], 'shuffle':'Yes', 'rarea':'Ellipse', 'rrange':'Exact'})
            bb_answer_text, html_answer_text = self.package.process_string(text)
            self.flow_mat1(response_label, bb_answer_text)
            classname="incorrect"
            if idx == correct:
                classname="correct"
            self.htmlfile += '<li class="'+classname+'">'+html_answer_text+'</li>'
            
        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'varequal', {'respident':'response', 'case':'No'}).text = a_uuids[correct]
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        for idx, luuid in enumerate(a_uuids):
            respcondition = etree.SubElement(resprocessing, 'respcondition')
            conditionvar = etree.SubElement(respcondition, 'conditionvar')
            etree.SubElement(conditionvar, 'varequal', {'respident':luuid, 'case':'No'})
            if idx == correct:
                etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '100'
            else:
                etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
            etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':luuid, 'feedbacktype':'Response'})
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.flow_mat2(itemfeedback, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.flow_mat2(itemfeedback, bb_neg_feedback_text)

        for idx, luuid in enumerate(a_uuids):
            itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':luuid, 'view':'All'})
            solution = etree.SubElement(itemfeedback, 'solution', {'view':'All', 'feedbackstyle':'Complete'})
            solutionmaterial = etree.SubElement(solution, 'solutionmaterial')
            self.flow_mat2(solutionmaterial, '')

        self.htmlfile += '</ul>'
        self.htmlfile += '<div>+:'+html_pos_feedback_text+'</div>'
        self.htmlfile += '<div>-:'+html_neg_feedback_text+'</div>'
        self.htmlfile += '</li>'
        print("Added MCQ "+repr(title))

    def addFITBQ(self, title, text, answers, positive_feedback="Good work", negative_feedback="That's not correct"):
        """Fill in the blank questions"""
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
        md = etree.SubElement(item, 'itemmetadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.package.bbid())+'_1'),
                ('bbmd_asitype', 'Item'),
                ('bbmd_assessmenttype', 'Pool'),
                ('bbmd_sectiontype', 'Subsection'),
                ('bbmd_questiontype', 'Fill in the Blank Plus'),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', 'N'),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', 'none'),
                ('bbmd_partialcredit', 'true'),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', '-1.0'),
                ('qmd_weighting', '0'),
                ('qmd_instructornotes', ''),
        ]:
            etree.SubElement(md, key).text = val
        
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})
        bb_question_text, html_question_text = self.package.process_string(text)
        self.htmlfile += '<li>'+html_question_text+'<ul>'
        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        for ans_key in answers:
            response_str = etree.SubElement(flow2, 'response_str', {'ident':ans_key, 'rcardinality':'Single', 'rtiming':'No'})
            render_fib = etree.SubElement(response_str, 'render_choice', {'charset':'us-ascii', "columns":"0", 'encoding':'UTF_8', 'fibtype':'String', 'maxchars':'0', 'maxnumber':'0', 'minnumber':'0', 'prompt':'Box', 'rows':'0'})

        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        and_tag = etree.SubElement(conditionvar, 'and')
        for ans_key, regex_exprs in answers.items():
            or_tag = etree.SubElement(and_tag, 'or')
            for regex in regex_exprs:
                etree.SubElement(or_tag, 'varsubset', {'respident':ans_key, 'setmatch':'Matches'}).text = regex
            self.htmlfile += '<li class="correct">'+regex+'</li>'
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})

        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.flow_mat2(itemfeedback, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.flow_mat2(itemfeedback, bb_neg_feedback_text)

        self.htmlfile += '</ul>'
        self.htmlfile += '<div>+:'+html_pos_feedback_text+'</div>'
        self.htmlfile += '<div>-:'+html_neg_feedback_text+'</div>'
        self.htmlfile += '</li>'        
        print("Added FITBQ "+repr(title))

    def addCalcNumQ(self, title, text, xs, count, calc, errfrac=None, erramt=None, errlow=None, errhigh=None, positive_feedback="Good work", negative_feedback="That's not correct"):
        #This fancy loop goes over all permutations of the variables in xs
        i = 0
        while True:
            if i >= count:
                break;
            x = {}
            # Calculate all random variables
            for xk in xs:
                if hasattr(xs[xk][0], 'rvs'):
                    x[xk] =  roundSF(xs[xk][0].rvs(1)[0], xs[xk][1]) #round to given S.F.
                elif isinstance(xs[xk][0], list):
                    x[xk] = random.choice(xs[xk][0]) #Random choice from list
                else:
                    raise RuntimeError("Unrecognised distribution/list for the question")

            # Run the calculation
            x = calc(x)
            
            if x is None:
                continue

            if 'erramt' in x:
                erramt = x['erramt']
            
            i += 1
            
            t = text
            pos = positive_feedback
            neg = negative_feedback
            for var, val in x.items():
                if isinstance(val, sympy.Basic):
                    t = t.replace('['+var+']', sympy.latex(val))
                    pos = pos.replace('['+var+']', sympy.latex(val))
                    neg = neg.replace('['+var+']', sympy.latex(val))
                else:
                    t = t.replace('['+var+']', str(val))
                    pos = pos.replace('['+var+']', str(val))
                    neg = neg.replace('['+var+']', str(val))
            
            self.addNumQ(title=title, text=t, answer=x['answer'], errfrac=errfrac, erramt=erramt, errlow=errlow, errhigh=errhigh, positive_feedback=pos, negative_feedback=neg)

            
    def flow_mat2(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'Block'})
        self.flow_mat1(flow, text)

    def flow_mat1(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'FORMATTED_TEXT_BLOCK'})
        self.material(flow, text)
        
    def material(self, node, text):
        material = etree.SubElement(node, 'material')
        mat_extension = etree.SubElement(material, 'mat_extension')
        mat_formattedtext = etree.SubElement(mat_extension, 'mat_formattedtext', {'type':'HTML'})
        mat_formattedtext.text = text
        
class Package:
    def __init__(self, courseID="IMPORT"):
        """Initialises a Blackboard package
        """
        self.courseID = courseID
        self.embedded_files = {}
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except:
            compression = zipfile.ZIP_STORED
        self.zf = zipfile.ZipFile(self.courseID+'.zip', mode='w', compression=compression)
        self.next_xid = 1000000
        self.equation_counter = 0
        self.resource_counter = 0
        self.embedded_paths = {}
        #Create the manifest file
        self.xmlNS = "http://www.w3.org/XML/1998/namespace"
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element("manifest", {'identifier':'man00001'}, nsmap={'bb':self.bbNS})
        organisations = etree.SubElement(self.manifest, "organizations")
        self.resources = etree.SubElement(self.manifest, 'resources')

        self.idcntr = 3191882
        self.latex_kwargs = dict()
        self.latex_cache = {}
        
    def bbid(self):
        self.idcntr += 1
        return self.idcntr

    def create_unique_filename(self, base, ext):
        count = 0
        while True:
            fname = base+'_'+str(count)+ext
            if not os.path.isfile(fname):
                return fname
            count += 1
    
    def close(self):
        #Write additional data to implement the course name
        parentContext = etree.Element("parentContextInfo")
        etree.SubElement(parentContext, "parentContextId").text = self.courseID
        self.embed_resource(self.courseID, "resource/x-mhhe-course-cx", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(parentContext, pretty_print=False).decode('utf-8'))

        #Finally, write the manifest file
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=False).decode('utf-8'))
        self.zf.writestr('.bb-package-info', open(os.path.join(os.path.dirname(__file__), '.bb-package-info')).read())
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def createPool(self, pool_name, *args, **kwargs):
        return Pool(pool_name, self, *args, **kwargs)

    def embed_resource(self, title, type, content):
        self.resource_counter += 1
        name = 'res'+format(self.resource_counter, '05')
        resource = etree.SubElement(self.resources, 'resource', {'identifier':name, 'type':type})
        resource.attrib[etree.QName(self.xmlNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS, 'file')] = name+'.dat'
        resource.attrib[etree.QName(self.bbNS, 'title')] = title
        
        self.zf.writestr(name+'.dat', content)

    def embed_file_data(self, name, content):
        """Embeds a file (given a name and content) to the quiz and returns the
        unique id of the file, and the path to the file in the zip
        """                

        #First, we need to process the path of the file, and embed xid
        #descriptors for each directory/subdirectory
        
        #Split the name into filename and path
        path, filename = os.path.split(name)

        #Simplify the path (remove any ./ items and simplify ../ items to come at the start)
        if (path != ""):
            path = os.path.relpath(path)
        
        #Split the path up into its components
        def rec_split(s):
            rest, tail = os.path.split(s)
            if rest in ('', os.path.sep):
                return [tail]
            return rec_split(s) + [tail]

        path = rec_split(path)
        root, ext = os.path.splitext(filename)

        def processDirectories(path, embedded_paths, i=0):
            #Keep processing until the whole path is processed
            if i >= len(path):
                return path

            #Slice any useless entries from the path
            if i==0 and (path[0] == ".." or path[0] == '/' or path[0] == ''):
                path = path[1:]
                return processDirectories(path, embedded_paths, i)

            #Check if the path is already processed
            if path[i] in embedded_paths:
                new_e_paths = embedded_paths[path[i]][1]
                path[i] = embedded_paths[path[i]][0]
            else:
                #Path not processed, add it
                descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
                relation = etree.SubElement(descriptor_node, 'relation')
                resource = etree.SubElement(relation, 'resource')

                self.next_xid += 1
                transformed_path = path[i]+'__xid-'+str(self.next_xid)+'_1'
                etree.SubElement(resource, 'identifier').text = str(self.next_xid)+'_1' + '#' + '/courses/'+self.courseID+'/' + os.path.join(*(path[:i+1]))
                embedded_paths[path[i]] = [transformed_path, {}]
                new_e_paths = embedded_paths[path[i]][1]

                path[i] = transformed_path
                
                self.zf.writestr(os.path.join('csfiles/home_dir', *(path[:i+1]))+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))

            return processDirectories(path, new_e_paths, i+1)

        processDirectories(path, self.embedded_paths)
        
        #Finally, assign a xid to the file itself
        self.next_xid += 1
        filename = root + '__xid-'+str(self.next_xid)+'_1' + ext

        #Merge the path pieces and filename
        path = path + [filename]
        path = os.path.join(*path)
        filepath = os.path.join('csfiles/home_dir/', path)
        self.zf.writestr(filepath, content)
        
        descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
        relation = etree.SubElement(descriptor_node, 'relation')
        resource = etree.SubElement(relation, 'resource')
        etree.SubElement(resource, 'identifier').text = str(self.next_xid) + '#' + '/courses/'+self.courseID+'/'+path
        self.zf.writestr(filepath+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))
        return str(self.next_xid)+'_1', filepath

    def embed_file(self, filename, file_data=None, attrib={}):
        """Embeds a file, and returns an img tag for use in blackboard, and an equivalent for html.
        """
        #Grab the file data
        if file_data == None:
            with open(filename, mode='rb') as file:
                file_data = file.read()
            
        #Check if this file has already been embedded
        if filename not in  self.embedded_files:
            xid, path = self.embed_file_data(filename, file_data)
            self.embedded_files[filename] = (xid, path)
            return xid, path
            
        #Hmm something already exists with that name, check the data
        xid, path = self.embedded_files[filename]
        fz = self.zf.open(path)
        if file_data == fz.read():
            #It is the same file! return the existing link
            return xid, path
        fz.close()
        
        #Try generating a new filename, checking if that already exists in the store too
        count=-1
        fbase, ext = os.path.splitext(filename)
        while True:
            count += 1 
            fname = fbase + '_'+str(count)+ext
            if fname in self.embedded_files:
                xid, path = self.embedded_files[fname]
                fz = self.zf.open(path)
                if file_data == fz.read():
                    return xid, path
                else:
                    continue
            break
        #OK we have a new unique name, fname. Use this to embed the file
        xid, path = self.embed_file_data(fname, file_data)
        self.embedded_files[fname] = (xid, path)
        return xid, path
        
                                
    def embed_image(self, filename, img_data=None, attrib={}):
        xid, path = self.embed_file(filename, img_data)
        output_bb = '<img src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+xid+'"'
        output_html = '<img src="'+path+'"'
        for key, value in attrib.items():
            output_bb += ' '+key+'="'+value+'"'
            output_html += ' '+key+'="'+value+'"'
        output_bb += '>'
        output_html += '>'
        return output_bb, output_html
        
    def embed_latex(self, formula, display=False):
        """Renders a LaTeX formula to an image, embeds the image in the quiz
        and returns a img tag which can be used in the text of a
        question or answer.
        """
        if formula in self.latex_cache:
            return self.latex_cache[formula]
        
        name = "LaTeX/eq"+str(self.equation_counter)+".png"
        self.equation_counter += 1

        img_data, width_px, height_px = render_latex(formula, display=display, **self.latex_kwargs)

        #This gives a 44px=1em height
        width_em = width_px / 44.0
        height_em = height_px / 44.0
        
        if display:
            attrib = {'style':'display:block;margin-left:auto;margin-right:auto;'}
        else:
            attrib = {'style':'vertical-align:middle;'}

        attrib['width'] = str(width_px)
        attrib['height'] = str(height_px)
        attrib['alt'] = escape(formula)
        self.latex_cache[formula] = self.embed_image(name, img_data, attrib=attrib)
        return self.latex_cache[formula]

    def process_string(self, in_string):
        """Scan a string for LaTeX equations, image tags, etc, and process them.
        """
        #Process img tags
        pattern = re.compile(r"<img.*?>")

        def img_src_processor(img_txt, html_mode):
            img_tag = html.fragment_fromstring(img_txt)
            xid, path = self.embed_file(img_tag.attrib['src'])
            if html_mode:
                img_tag.attrib['src'] = path
            else:
                img_tag.attrib['src'] = '@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+xid
            return html.tostring(img_tag).decode('utf-8')

        html_string = pattern.sub(lambda match : img_src_processor(match.group(0), True), in_string)
        in_string = pattern.sub(lambda match : img_src_processor(match.group(0), False), in_string)
                    
        in_string = in_string.split('$$')
        html_string = html_string.split('$$')
        for i in range(1, len(in_string), 2):
            bb_img, html_img = self.embed_latex(in_string[i], True)
            in_string[i] = bb_img
            html_string[i] = html_img
        in_string = ''.join(in_string)
        html_string = ''.join(html_string)

        #Process inline LaTeX equations
        in_string = in_string.split('$')
        html_string = html_string.split('$')
        for i in range(1, len(in_string), 2):
            bb_img, html_img = self.embed_latex(in_string[i], False)
            in_string[i] = bb_img
            html_string[i] = html_img

        return ''.join(in_string), ''.join(html_string)
