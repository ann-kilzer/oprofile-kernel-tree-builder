#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

"""Builds a ctags file for use with Oprofile Kernel Tree Builder.

This python script is designed to build a ctags file excluding certain unneeded
directories.  The script just needs the path to the kernel and the architecture:

   $ python mk_tags.py -p <path to kernel> -a <arch>

Upon completion, there should be a file called tags with the ctags.
"""

__author__ = 'akilzer@gmail.com (Ann Kilzer)'

import commands, re
from optparse import OptionParser


def MkRegEx(path, arch):
  """Creates a regular expression of items we want."""
  kernel_root = r'^' + path
  patterns = []
  # here is the stuff we want
  patterns.append(r'include/asm-generic/')
  patterns.append(r'arch/' + arch + r'/')
  patterns.append(r'include/asm-' + arch + r'/')
  return '|'.join(list(kernel_root + l for l in patterns))


def BadRegEx(path):
  """Creates a regular expression of items we do not want."""
  kernel_root = r'^' + path
  patterns = []
  # here is the stuff we don't want!
  patterns.append(r'Documentation/')
  patterns.append(r'drivers/s390/')
  patterns.append(r'include/asm-')  # make sure bad is after good
  patterns.append(r'arch/')         # make sure bad is after good
  return '|'.join(list(kernel_root + l for l in patterns))


def MkKernelCtags(path, arch):
  """Creates the ctags file, omitting unneeded files."""
  l = commands.getoutput("find " + path +
                         " -follow -name '*.[chCH]' -print").split()

  ctags_files = []
  while l:
    i = l.pop()
    if re.search(MkRegEx(path, arch), i):
      ctags_files.append('./' + i[len(path):])
    elif re.search(BadRegEx(path), i):
      pass
    else:
      ctags_files.append('./' + i[len(path):])

  print commands.getstatusoutput('cd ' + path + '; ctags ' + ' '.join(ctags_files))

if __name__ == '__main__':
  parser = OptionParser()
  parser.add_option('-p', '--path', dest='path',
                    help='path to kernel', metavar='PATH')
  parser.add_option('-a', '--arch', dest='arch', help='architecture',
                    metavar='ARCH')

  (options, args) = parser.parse_args()
  if not options.path:
    print 'Error: Need to specify path (-p)'
  elif not options.arch:
    print 'Error: Need to specify architecture (-a)'
  else:
    MkKernelCtags(options.path, options.arch)
