#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re

parser = argparse.ArgumentParser( description = "Git-ja utilities for gitjas!" )
parser.add_argument( '-d', '--debug', action = 'store_true', help = "Enable debug output" )
parser.add_argument( '-r', '--remotes', action = 'store_true', help = "List all remotes" )
parser.add_argument( '-u', '--update', action = 'store_true', help = "Update info about all remotes" )
parser.add_argument( '-t', '--status', action = 'store_true', help = "Show divergence between given refs and their remote tracked and homonym branches" )
parser.add_argument( '-i', '--divergence', action = 'store_true', help = "Show divergence tree between given refs" )
parser.add_argument( '-f', '--syncLog', action = 'store_true', help = "Get the commits that differ between local and tracked branches" )
parser.add_argument( '-P', '--prune', action = 'store_true', help = "Prune remote branches. If no remote branches are given, origin branches that doesn't exist locally will be used" )
parser.add_argument( '-s', '--shy', action = 'store_true', help = "Do not execute any remote query" )
parser.add_argument( 'refs', metavar='ref', nargs='*' )
doneStuff = False
parseRes = parser.parse_args()

colorMap = ( 'black', 'red', 'green', 'orange', 'blue', 'violet', 'lightblue', 'gray', 'darkgray', 'inv' )
def colorize( msg, color ):
  iC = max( 0, colorMap.index( color.lower() ) )
  return "\033[;3%dm%s\033[0m" % ( iC, msg )

def debugMsg( msg ):
  if parseRes.debug:
    print "[%s] %s" %( colorize( 'DEBUG', 'lightblue' ), msg )

def errorMsg( msg ):
  if parseRes.debug:
    print "[%s] %s" %( colorize( 'ERROR', 'red' ), msg )
    

def magicSplit( data, char = None ):
  return [ f.strip() for f in data.split( char ) if f.strip() ]
 
def getTrackedBranch( head ):
  remote = do( "git for-each-ref --format='%%(upstream:short)' refs/heads/%s" % head )
  return remote.strip()
  
def getSameRefInRemotes( head ):
  remBranch = []
  remBrRE = re.compile( "^\*?\s*([\w-]+)/([\w-]+)\s*$" )
  for ref in do( "git branch -r" ).split( "\n" ):
    match = remBrRE.match( ref )
    if match:
      groups = match.groups()
      if groups[1] == head:
        remBranch.append( "%s/%s" % ( groups[0], groups[1] ) )
  return remBranch

def parentOf( parent, child ):
  return parent in magicSplit( do( "git branch --merged %s" % child ), "\n" )
  
def exists( ref ):
  return do( "git rev-parse %s" % ref, checkValid = True )

def getAllLocalBranches():
  return [ com.lstrip( '*' ).strip() for com in do( "git branch" ).split( "\n" ) if com.strip() ]
  
def getCurrentBranch():
  for line in magicSplit( do( "git branch" ), "\n" ):
    if line[0] == '*':
      return line[1:].strip()
  return None
  
def getRefs( defaultAll = False, defaultCurrent = False ):
  if parseRes.refs:
    refs = parseRes.refs
    iP = refs.index( 'ALL' )
    if iP > -1:
      refs.pop(iP)
      for localBranch in getAllLocalBranches():
        if localBranch not in refs:
          refs.append( localBranch )
    for ref in parseRes.refs:
      if not exists( ref ):
        print "Ref %s doesn't seem to be valid" % colorize( ref, 'red' )
        sys.exit(1)
  elif defaultAll:
    refs = getAllLocalBranches()
  elif defaultCurrent:
    refs = [ getCurrentBranch() ]
  else:
    refs = []
  return refs
      

def getCommitHash( head ):
  return do( "git log -n 1 --pretty=format:%%H %s" % head )
 
def do( cmd, checkValid = False ):
  debugMsg( "Exec %s" % cmd )
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
    err = sp.stderr.read()
    if not err:
      err = data
    if checkValid:
      return False
    errorMsg( "While executing [%s]:\n%s" % ( cmd, err ) )
    sys.exit( wait )
  if checkValid:
    return True
  sp.stderr.close()
  sp.stdout.close()
  return data.rstrip()

#Actual stuff
  
def execRemotes():
  remotes = magicSplit( do( "git remote show" ) )
  print "%s remotes: %s" % ( len( remotes ), ", ".join( remotes ) )
  for remote in remotes:
    cmd = "git remote show %s" % remote
    if parseRes.shy:
      cmd += " -n"
    print do( cmd )

def execUpdate():
  print "Updating remotes..."
  print do( "git remote update --prune" )
  
def execDivergence():
  refs = getRefs( defaultAll = True )
  if len( refs ) == 1:
    remoteTracked = getTrackedBranch( refs[0] )
    if remoteTracked:
      refs.append( remoteTracked )
    else:
      errMsg( "%s is not tracking any remote branch" % refs[0] )
      return
  showDivergenceTree( refs )
      
def showDivergenceTree( refs ):
  mergeBase = do( "git merge-base --octopus %s" % " ".join( refs ) )
  iP = 0
  while iP < len( refs ):
    if mergeBase == getCommitHash( refs[iP] ):
      mergeBase = refs[iP]
      refs.pop( iP )
      break
    iP += 1
  if not refs:
    print "There is no history betweed defined refs"
  else:
    cmd = "git log --graph --color --pretty=format:%s %s^! %s" % ( "%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s", mergeBase, " ".join( refs ) )
    print do( cmd )

def execSyncLog():
  remlog = re.compile( "^ *\*? +([\-\w]+) +\w+ +\[(ahead|behind) +([0-9]+)\].*$" )
  refs = getRefs( defaultCurrent = True )
  found = {}
  for line in do( "git branch -v" ).split( "\n" ):
    match = remlog.match( line )
    if match:
      groups = match.groups()
      if groups[0] in refs:
        found[ groups[0] ] = ( groups[1], int( groups[2] ) )
  debugMsg( "Using refs %s" % ", ".join( refs ) )
  for ref in refs:
    if ref not in found:
      continue
    trackedBranch = getTrackedBranch( ref )
    if not trackedBranch:
      print "%s is not tracking any remote brach"
      continue
    if found[ ref ][0] == 'ahead':
      print "\033[;35m*\033[0m %s is \033[;35mAHEAD\033[0m of %s by %d refs:\n" % ( ref, trackedBranch, found[ ref ][1] )
      sTo = ( getTrackedBranch( ref ), ref )
    else:
      print "\033[;35m*\033[0m %s is \033[;35mBEHIND\033[0m of %s by %d refs:\n" % ( ref, trackedBranch, found[ ref ][1] )
      sTo = ( ref, getTrackedBranch( ref ) )
    print "%s\n" % do( "git log --color '--pretty=format:%%Cgreen%%H %%Cblue%%d%%Creset%%n%%B' %s..%s" % sTo )

def execStatus():
  refs = getRefs( defaultCurrent = True )
  for ref in refs:
    statusRefs = [ ref ]
    remoteTracked = getTrackedBranch( ref )
    if remoteTracked:
        statusRefs.append( remoteTracked )
    statusRefs.extend( getSameRefInRemotes( ref ) )
    if len( statusRefs ) == 1:
      print "%s has no remote tracked nor homonym branches"
      continue
    print "%s Showing divergence for %s with %s" % ( colorize( '->', 'lightblue' ), 
                                                    statusRefs[0], 
                                                    ", ".join( statusRefs[1:] ) )
    showDivergenceTree( statusRefs )
    
def execPrune():
  if not parseRes.shy:
    execUpdate()
  refsToDelete = getRefs()
  remoteBranches = []
  for branch in do( "git branch -r" ).split( "\n" ):
    branch = branch.strip()
    if branch.find( "origin/HEAD" ) == -1:
      remoteBranches.append( branch )
  auto = False
  if refsToDelete:
    for ref in refsToDelete:
      if ref not in remoteBranches:
        print "%s is not a remote branch" % ref
        sys.exit(1)
  else:
    auto = True
    for branch in remoteBranches:
      if branch.find( "origin/" ) == 0:
        refsToDelete.append( branch )
  if auto:
    iP = 0
    while iP < len( refsToDelete ):
      branch = refsToDelete[iP].split( "/" )[1]
      if exists( branch ):
        refsToDelete.pop( iP )
      elif raw_input( "%s does not exist locally. Prune? [Y/n]> " % branch ).lower() not in ( 'y', 'yes' ):
        refsToDelete.pop( iP )
      else:
        iP += 1
  if not refsToDelete:
    print "No remote branches found to be pruned"
  else:
    if raw_input( "About to prune %s. Is it OK? [Y/n]> " % ", ".join( refsToDelete ) ).lower() not in ( 'y', 'yes' ):
      print "Prune aborted"
    else:
      for ref in refsToDelete:
        print "Pruning %s" % ref
        if parseRes.shy:
          print "Skipping prune due to shy command"
        else:
          do( "git push %s :%s" % tuple( ref.split( "/" ) ) )

  
#Glue code
  
if parseRes.remotes:
  doneStuff = True
  execRemotes()
if parseRes.update:
  doneStuff = True
  execUpdate()
if parseRes.divergence:
  doneStuff = True
  execDivergence()
if parseRes.syncLog:
  doneStuff = True
  execSyncLog() 
if parseRes.prune:
  doneStuff = True
  execPrune()
if parseRes.status:
  doneStuff = True
  execStatus()
  
if not doneStuff:
  parser.print_help()
  sys.exit( 1 )
