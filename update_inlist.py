#!/usr/bin/env python

import argparse
import datetime
import logging
import os
import re
import sys
import tempfile

# what form must inlist lines have
LINE_REGEX="(?P<front>[! \t]+)(?P<name>[^! \t]+)[ \t]*=[ \t]*(?P<value>[^! \t\n]+)"

# when you add a line, what should the format be?
NEWLINE_TEMPLATE="{front}{name} = {value} ! {blame}\n"

# how should update_inlist indicate it made a modification
BLAME_TEMPLATE="Modified by update_inlist.py, {timestamp}"

# how should the file be indented
STD_INDENT="    "

def main(args):

    # configure logging
    logging.basicConfig(stream=sys.stderr, format='%(levelname)s: %(message)s',
                        level = logging.INFO)

    for filename in args.filename:

        # open the inlist file to be modified
        try:
            inlist_file=open(filename,'r')
        except IOError:
            logging.error('Failed to open inlist file: {0}'.format(filename))
            sys.exit(1)

        # open a temporary file to hold modifications
        try:
            fd,tmpfile=tempfile.mkstemp(suffix='.inlist', prefix='update',
                                        dir=os.path.abspath(os.getcwd()),
                                        text=True)
            os.close(fd)
            fout = open(tmpfile, 'w')
        except IOError:
            logging.error('Failed to open temporary file: {0}'.format(tmpfile))
            sys.exit(1)


        # make dictionaries of name:values pairs
        args.add = dict(args.add)
        args.modify = dict(args.modify)

        # call the function that does all the work
        new_inlist = update_inlist(inlist_file, **vars(args))

        # write data
        fout.write("".join(new_inlist))

        inlist_file.close()
        fout.close()

        # overwrite old file with new
        os.rename(tmpfile,filename)

        logging.info("File %s updated" % filename)

    return


def update_inlist(inlist_file, add, modify, delete,
                  comment, uncomment, section, **kwargs):

    # timestamp the blamestring
    now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    blame=BLAME_TEMPLATE.format(timestamp=now)

    currentsection=None
    new_inlist_lines = []

    # go through the file lie by line and determine what should happen
    for line in inlist_file:

        # does this look like an inlist option line?
        line_match = re.match(LINE_REGEX, line)

        # do we know where we are?
        if currentsection is not None:
            # yes
            if section and currentsection not in section:
                # if we should only look at one section this isn't in
                # leave the line unchanged and then continue
                new_inlist_lines.append(line)
                continue
        else:
            # no: don't do anything except look for where we are
            line_match = None

        if line_match is not None:

            # line matched, now get the values
            front = line_match.group('front')
            name = line_match.group('name')
            value = line_match.group('value')

            # and now do as instructed with them
            if name in comment:
                if "!" not in front:
                    front = front + "!"
                logging.debug("commented {0} {1}".format(name,value))

            if name in uncomment:
                front = re.sub('!',"",front)
                logging.debug("uncommented {0} {1}".format(name,value))

            if name in modify:
                value = modify[name]
                logging.debug("modified {0} {1}".format(name,value))

            if name not in delete:
                newline=NEWLINE_TEMPLATE.format(front=front,
                                                name=name,
                                                value=value,
                                                blame=blame)

                new_inlist_lines.append(newline)
            else:
                logging.debug("deleted {0} {1}".format(name,value))

        else:

            # this wasn't an inlist option line

            # is it the start of a section?
            if line.startswith('&'):

                # save which section it is
                currentsection = line[1:].strip()
                new_inlist_lines.append(line)

                logging.debug("Start section: {}".format(currentsection))

                # add all new options at top
                for name,value in add.iteritems():

                    logging.debug("added {0} {1}".format(name,value))
                    newline=NEWLINE_TEMPLATE.format(front=STD_INDENT,
                                                    name=name,
                                                    value=value,
                                                    blame=blame)
                    new_inlist_lines.append(newline)

            # is this the end of a section?
            elif line.startswith('/'):

                logging.debug("End section: {0}".format(currentsection))
                currentsection = None
                new_inlist_lines.append(line)

            # is this anything else?
            else:
                # leave the line untouched
                new_inlist_lines.append(line)

    return new_inlist_lines


######################################################################

if __name__=="__main__":

    parser = argparse.ArgumentParser(argument_default = [],)

    parser.add_argument('-a', "--add", nargs=2, action='append',
                        metavar = ("name", "value"),
                        help="add parameter",)

    parser.add_argument('-m', "--modify", nargs=2, action='append',
                        metavar = ("name", "value"),
                        help="modify parameter")

    parser.add_argument('-d', "--delete", action='append',
                        metavar = ("name",),
                        help="delete parameter")

    parser.add_argument('-c', "--comment", action='append',
                        metavar = ("name",),
                        help="comment parameter")
    parser.add_argument('-u', "--uncomment", action='append',
                        metavar = ("name",),
                        help="uncomment parameter")


    parser.add_argument('-s', "--section", metavar = ("name",),
                        help="limit modifications to one section")

    parser.add_argument('filename', nargs='+', metavar = "filename",
                        help="filename of inlist to modify")

    args = parser.parse_args()
    main(args)
