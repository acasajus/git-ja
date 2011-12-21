#!/usr/bin/env python

import argparse
import sys
import subprocess
import os

parser = argparse.ArgumentParser( description = "Git remote manager" )
parser.add_argument( '-l', '--list', action = 'store_true', help = "List all remotes" )
parser.add_argument( '-u', '--update', action = 'store_true', help = "Update all remotes" )
parser.add_argument( '-t', '--status', action = 'store_true', help = "Show status of all branches with remotes" )
parser.add_argument( '-d', '--divergence', action = 'store_true', help = "Show divergence tree of given commits" )
parser.add_argument( '-s', '--shy', action = 'store_true', help = "Do not execute any remote query" )
parser.add_argument( 'commits', metavar='commit', nargs='*' )
doneStuff = False
parseRes = parser.parse_args()


def magicSplit( data, char = None ):
  return [ f.strip() for f in data.split( char ) if f.strip() ]

def do( cmd, native = False ):
  if native:
    return os.system( cmd )
  sp = subprocess.Popen( cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
  data = ""
  stepRead = 8192
  while True:
    buf = sp.stdout.read( stepRead )
    if buf:
      data += buf
    if len( buf ) < stepRead:
      break
  wait = sp.wait()
  if wait != 0:
    print "ERROR while executing [%s]:\n%s" % ( cmd, sp.stderr.read() )
    sys.exit( wait )
  sp.stderr.close()
  sp.stdout.close()
  return data.rstrip()

if parseRes.list:
  doneStuff = True
  remotes = magicSplit( do( "git remote show" ) )
  print "%s remotes: %s" % ( len( remotes ), ", ".join( remotes ) )
  for remote in remotes:
    cmd = "git remote show %s" % remote
    if parseRes.shy:
      cmd += " -n"
    print do( cmd )
if parseRes.update:
  doneStuff = True
  print "Updating remotes..."
  print do( "git remote update --prune" )
if parseRes.divergence:
  doneStuff = True
  if parseRes.commits:
    commits = parseRes.commits
  else:
    commits = [ com.lstrip( '*' ).strip() for com in do( "git br" ).split( "\n" ) if com.strip() ]
  mergeBase = do( "git merge-base --octopus %s" % " ".join( commits ) )
  if not commits:
    commits = [ "HEAD" ]
  cmd = "git log --graph --color --pretty=format:%s %s^..%s" % ( "%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s", mergeBase, " ".join( commits ) )
  print do( cmd )




if not doneStuff:
  parser.print_help()
  sys.exit( 1 )
