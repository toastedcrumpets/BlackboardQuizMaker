#!/usr/bin/env python

from lxml import etree
import lxml.html as html
import time
import zipfile
import re
import os
import uuid
from xml.sax.saxutils import escape, unescape
from PIL import Image
from StringIO import StringIO

import subprocess
dn = os.path.dirname(os.path.realpath(__file__))
def render_latex(formula):
    """Renders LaTeX expression to bitmap image data.
    """

    subprocess.check_call([os.path.join(dn, 'tex2im'), '-r', '100x100', '{'+formula+'}'])

    with open('out.png', 'rb') as f:
        data = f.read()
        
    im = Image.open(StringIO(data))
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

        rubric = etree.SubElement(assessment, 'rubric', {'view':'All'})
        flow_mat = etree.SubElement(rubric, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, instructions)

        presentation_material = etree.SubElement(assessment, 'presentation_material')
        flow_mat = etree.SubElement(presentation_material, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, description)

        self.section = etree.SubElement(assessment, 'section')
        
        #Create the HTML file for preview
        self.htmlfile = "<html><head><style>li.correct, li.incorrect{list-style-type:none;} li.correct:before{content:'\\2713\\0020'}\nli.incorrect:before{content:'\\2718\\0020'}</style></head><body><p>Questions<ol>"

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.preview:
            self.package.zf.writestr(self.pool_name+'_preview.html', self.htmlfile+'</ol></body></html>')
        self.package.embed_resource("assessment/x-bb-qti-pool", '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(self.questestinterop, pretty_print=False))
        
    def addNumQ(self, title, text, answer, errfrac=None, erramt=None, errlow=None, errhigh=None, positive_feedback="Good work", negative_feedback="That's not correct"):
        if not errfrac and not erramt and ((not errlow) or (not errhigh)):
            raise Exception("Numerical questions require an error amount, fraction, or bounds")
        if errfrac != None:
            errlow = answer * (1-errfrac)
            errhigh = answer * (1+errfrac)
        if erramt != None:
            errlow = answer - abs(erramt)
            errhigh = answer + abs(erramt)
        
        self.question_counter += 1 
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
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
        
        self.htmlfile += '</ul>'
        self.htmlfile += '<div>+:'+html_pos_feedback_text+'</div>'
        self.htmlfile += '<div>-:'+html_neg_feedback_text+'</div>'
        self.htmlfile += '</li>'

        
    def addMCQ(self, title, text, answers, correct, positive_feedback="Good work", negative_feedback="That's not correct"):
        if not errfrac and not erramt and ((not errlow) or (not errhigh)):
            raise Exception("Numerical questions require an error amount, fraction, or bounds")
        if errfrac != None:
            errlow = answer * (1-errfrac)
            errhigh = answer * (1+errfrac)
        if erramt != None:
            errlow = answer + abs(erramt)
            errhigh = answer - abs(erramt)
        
        self.question_counter += 1 
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        item = etree.SubElement(self.section, 'item', {'title':title, 'maxattempts':'0'})
        presentation = etree.SubElement(item, 'presentation')
        flow1 = etree.SubElement(presentation, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'QUESTION_BLOCK'})
        flow3 = etree.SubElement(flow2, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})

        bb_question_text, html_question_text = self.package.process_string(text)
        self.htmlfile += '<li>'+html_question_text+'<ul>'
        self.material(flow3, bb_question_text)

        flow2 = etree.SubElement(flow1, 'flow', {'class':'RESPONSE_BLOCK'})
        response_lid = etree.SubElement(flow2, 'response_lid', {'ident':'response', 'rcardinality':'Single', 'rtiming':'No'})
        render_choice = etree.SubElement(response_lid, 'render_choice', {'shuffle':'No', 'minnumber':'0', 'maxnumber':'0'})

        a_uuids = []
        for idx,text in enumerate(answers):
            flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
            a_uuids.append(uuid.uuid4().hex)
            response_label = etree.SubElement(flow_label, 'response_label', {'ident':a_uuids[-1], 'shuffle':'Yes', 'rarea':'Ellipse', 'rrange':'Exact'})
            bb_answer_text, html_answer_text = self.package.process_string(text)
            self.flow_mat1(response_label, bb_answer_text)
            classname="incorrect"
            if (idx+1 == correct):
                classname="correct"
            self.htmlfile += '<li class="'+classname+'">'+html_answer_text+'</li>'
            
        resprocessing = etree.SubElement(item, 'resprocessing', {'scoremodel':'SumOfScores'})
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        decvar = etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'varequal', {'respident':'response', 'case':'no'}).text = a_uuids[correct]
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
        for idx, uuid in enumerate(a_uuids):
            respcondition = etree.SubElement(resprocessing, 'respcondition')
            conditionvar = etree.SubElement(respcondition, 'conditionvar')
            etree.SubElement(conditionvar, 'varequal', {'respident':uuid, 'case':'no'}).text = repr(answer)
            if idx == correct:
                etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '100'
            else:
                etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
            etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':uuid, 'feedbacktype':'Response'})
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'correct', 'view':'All'})
        flow1 = etree.SubElement(itemfeedback, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        self.material(flow2, bb_pos_feedback_text)
        
        itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':'incorrect', 'view':'All'})
        flow1 = etree.SubElement(itemfeedback, 'flow', {'class':'Block'})
        flow2 = etree.SubElement(flow1, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        self.material(flow2, bb_neg_feedback_text)

        for idx, uuid in enumerate(a_uuids):
            itemfeedback = etree.SubElement(item, 'itemfeedback', {'ident':uuid, 'view':'All'})
            solution = etree.SubElement(itemfeedback, 'solution', {'view':'All', 'feedbackstyle':'Complete'})
            solutionmaterial = etree.SubElement(solution, 'solutionmaterial')
            self.flow_mat1(solutionmaterial, '')

        
        gradable = etree.SubElement(q_node, 'GRADABLE')
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        etree.SubElement(gradable, 'FEEDBACK_WHEN_CORRECT').text = bb_pos_feedback_text
        etree.SubElement(gradable, 'FEEDBACK_WHEN_INCORRECT').text = bb_neg_feedback_text
        etree.SubElement(gradable, 'CORRECTANSWER', {'answer_id':question_id+'_a'+str(correct)})

        self.htmlfile += '</ul>'
        self.htmlfile += '<div>+:'+html_pos_feedback_text+'</div>'
        self.htmlfile += '<div>-:'+html_neg_feedback_text+'</div>'
        self.htmlfile += '</li>'

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
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element("manifest", {'identifier':'man00001'}, nsmap={'bb':self.bbNS})
        organisations = etree.SubElement(self.manifest, "organizations")
        self.resources = etree.SubElement(self.manifest, 'resources')

        
    def close(self):
        #Write additional data to implement the course name
        parentContext = etree.Element("parentContextInfo")
        etree.SubElement(parentContext, "parentContextId").text = self.courseID
        self.embed_resource("resource/x-mhhe-course-cx", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(parentContext, pretty_print=False))

        #Finally, write the manifest file
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=False))

        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def createPool(self, pool_name, *args, **kwargs):
        return Pool(pool_name, self, *args, **kwargs)

    def embed_resource(self, type, content):
        self.resource_counter += 1
        name = 'res'+format(self.resource_counter, '05')
        resource = etree.SubElement(self.resources, 'resource', {'identifier':name, 'type':type})
        resource.attrib[etree.QName(self.bbNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS, 'file')] = name+'.dat'
        
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
                
                self.zf.writestr(os.path.join('csfiles/home_dir', *(path[:i+1]))+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False))

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
        self.zf.writestr(filepath+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False))
        return str(self.next_xid)+'_1', filepath

    def embed_file(self, filename, file_data=None, attrib={}):
        """Embeds a file, and returns an img tag for use in blackboard, and an equivalent for html.
        """
        #Check if it is a real file being embedded
        if file_data == None:
            #Check if this file has already been embedded
            if filename in self.embedded_files:
                #It has, return the already embedded data
                return self.embedded_files[filename]

            #It has not, load the data
            with open(filename, mode='rb') as file:
                file_data = file.read()
            xid, path = self.embed_file_data(filename, file_data)
            self.embedded_files[filename] = (xid, path)
            return xid, path
        else:
            return self.embed_file_data(filename, file_data)

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
        name = "LaTeX/eq"+str(self.equation_counter)+".png"
        self.equation_counter += 1

        img_data, width_px, height_px = render_latex(formula)

        #This gives a 44px=1em height
        width_em = width_px / 44.0
        height_em = height_px / 44.0
        
        if display:
            formula = (r'\displaystyle ')+formula
            attrib = {'style':'display:block;margin-left:auto;margin-right:auto;'}
        else:
            attrib = {'style':'vertical-align:middle;'}

        attrib['width'] = str(width_px)
        attrib['height'] = str(height_px)
        attrib['alt'] = escape(formula)
        
        return self.embed_image(name, img_data, attrib=attrib)

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
            return html.tostring(img_tag)

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
