#!/usr/bin/env python

import argparse
import sys
import inspect
import subprocess
import logging

log = logging.getLogger( __name__ )
log.addHandler( logging.StreamHandler() )
log.setLevel( logging.INFO )

class Command( object ):

  def __init__( self, parser ):
    self.parser = parser
    self.shy = False
    self.parser.description = self.description()
    self.parser.usage = "git-ja {} [opts]".format( self.name() )

  @classmethod
  def name( cls ):
    return cls.__name__.lower()

  @classmethod
  def description( cls ):
    return "FILL THIS YOU LAZY DOG"

  def arm( self ):
    pass

  def fire( self ):
    self.opts = self.parser.parse_args( sys.argv[2:] )
    self.shy = self.opts.shy
    if self.opts.debug:
      log.setLevel( logging.DEBUG )
    return self.work( self.opts )

  def run( self, cmd, checkValid = False ):
    log.debug( "Exec %s" % cmd )
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
      log.error( "While executing [%s]:\n%s" % ( cmd, err ) )
      sys.exit( wait )
    if checkValid:
      return True
    sp.stderr.close()
    sp.stdout.close()
    return data.strip()

  def gitCurrentBranch( self ):
    return self.run( "git rev-parse --abbrev-ref HEAD" )

  def gitLocalBranches( self ):
    return [ line.split( "/" )[-1] for line in self.run( "git show-ref --heads" ).split( '\n' ) ]


class Promote( Command ):

  @classmethod
  def description( cls ):
    return "Send branch to remote"

  def arm( self ):
    self.parser.add_argument( "-r", "--remote", action = 'store', default = 'origin', help = 'Promote to this remote' )
    self.parser.add_argument( "-x", "--remote_branch", action = 'store', default = False, help = 'Remote branch to promote to' )
    self.parser.add_argument( "-u", "--upstream", action = 'store_true', default = False, help = 'Set upstream for git push/pull' )
    self.parser.add_argument( 'branches', metavar = 'branches', nargs = argparse.REMAINDER, help = "Branches to promote" )

  def work( self, opts ):
    if opts.upstream:
      basecmd = "git push -u"
    else:
      basecmd = "git push"
    branches = opts.branches
    if not branches:
      branches = [ self.gitCurrentBranch() ]
    for branch in branches:
      remname = opts.remote_branch
      if not remname:
        remname = branch
      log.info( "Promoting {} to {}/{}".format( branch, opts.remote, remname ) )
      if not self.run( "{} {} {}:{}".format( basecmd, opts.remote, branch, remname ) ):
          return False
    return True


class GitJa( object ):

  def __init__( self ):
    self.__cmds = dict( [ ( cls.name(), cls ) for cls in Command.__subclasses__() ] )
    mx = max( [ len( k ) for k in self.__cmds ] )

    usecmd = "\n  ".join( [ "{}: {}".format( k.rjust( mx ), self.__cmds[k].description() ) for k in self.__cmds ] )
    usage = "git-ja command [opts]\n\nAvailable commands:\n  {}".format( usecmd )

    self.__parser = argparse.ArgumentParser( description = "Git-ja utilities for gitjas!",
                                           usage = usage,
                                           formatter_class = argparse.RawDescriptionHelpFormatter )
    self.__parser.add_argument( '-d', '--debug', action = 'store_true', default = False, help = "Enable debug output" )
    self.__parser.add_argument( '-s', '--shy', action = 'store_true', default = False, help = "Do not execute any remote query" )

  def __searchCommand( self ):
    if len( sys.argv ) < 2:
      log.error( "Missing command" )
      return False
    q = sys.argv[1]
    if q in self.__cmds:
      return self.__cmds[q]
    cmds = [ k for k in self.__cmds ]
    for iP in range( len( q ) ):
      c = q[iP]
      cmds = [ k for k in cmds if len( k ) > iP and k[iP] == c ]
      if len( cmds ) == 1:
        return self.__cmds[ cmds[ 0 ] ]
    if len( cmds ) > 1:
      log.error( "Ambiguous command. Which one of {} is it?".format( cmds ) )
      return False
    log.error( "Unknown command" )
    return False

  def act( self ):
    cmdClass = self.__searchCommand()
    if not cmdClass:
      self.__parser.print_help()
      return False
    cmd = cmdClass( self.__parser )
    cmd.arm()
    return cmd.fire()

if __name__ == "__main__":
  gitja = GitJa()
  if gitja.act():
    sys.exit(0)
  else:
    sys.exit(1)


sys.exit(0)

colorMap = ( 'black', 'red', 'green', 'orange', 'blue', 'violet', 'lightblue', 'gray', 'darkgray', 'inv' )
def colorize( msg, color ):
  iC = max( 0, colorMap.index( color.lower() ) )
  return "\033[;3%dm%s\033[0m" % ( iC, msg )

def debugMsg( msg ):
  if parseRes.debug:
    print "[%s] %s" % ( colorize( 'DEBUG', 'lightblue' ), msg )

def errorMsg( msg ):
  if parseRes.debug:
    print "[%s] %s" % ( colorize( 'ERROR', 'red' ), msg )


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
    try:
      iP = refs.index( 'ALL' )
    except ValueError:
      iP = -1
    if iP > -1:
      refs.pop( iP )
      for localBranch in getAllLocalBranches():
        if localBranch not in refs:
          refs.append( localBranch )
    for ref in parseRes.refs:
      if not exists( ref ):
        print "Ref %s doesn't seem to be valid" % colorize( ref, 'red' )
        sys.exit( 1 )
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
      errorMsg( "%s is not tracking any remote branch" % refs[0] )
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
      sTo = ( getTrackedBranch( ref ), ref )
    else:
      sTo = ( ref, getTrackedBranch( ref ) )
    print "%s %s is %s of %s by %d refs:\n" % ( colorize( '*', 'violet' ), ref, colorize( found[ ref ][0].upper(), 'violet' ), trackedBranch, found[ ref ][1] )
    print "%s\n" % do( "git log --color '--pretty=format:%%Cgreen%%H %%Cblue%%d%%Creset%%n%%B' %s..%s" % sTo )

def execStatus():
  refs = getRefs( defaultCurrent = True )
  for ref in refs:
    statusRefs = [ ref ]
    remoteTracked = getTrackedBranch( ref )
    if remoteTracked:
        statusRefs.append( remoteTracked )
    for ref in getSameRefInRemotes( ref ):
      if ref not in statusRefs:
        statusRefs.append( ref )
    if len( statusRefs ) == 1:
      print "%s %s has no remote tracked nor homonym branches" % ( colorize( '->', 'red' ), statusRefs[0] )
      continue
    print "\n%s Showing divergence for %s with %s\n" % ( colorize( '->', 'lightblue' ),
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
        sys.exit( 1 )
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

def execFForward():
  if do( "git diff-index HEAD" ):
    print "Your working space is dirty. Commit first all changes!"
    sys.exit( 1 )
  if not parseRes.shy:
    execUpdate()
  refsToForward = getRefs( defaultAll = True )
  currentBranch = getCurrentBranch()
  wBranch = currentBranch
  for branch in refsToForward:
    trackedBranch = getTrackedBranch( branch )
    debugMsg( "Trying %s -> %s" % ( branch, trackedBranch ) )
    if not trackedBranch:
      continue
    if not do( "git rev-list %s..%s" % ( branch, trackedBranch ) ):
      debugMsg( "%s is not ahead of %s" % ( trackedBranch, branch ) )
      continue
    if do( "git rev-list %s..%s" % ( trackedBranch, branch ) ):
      print "%s and %s have diverged, need a manual merge" % ( branch, trackedBranch )
      continue
    print "Fast forwarding %s to %s" % ( branch, trackedBranch )
    do( "git checkout %s" % branch )
    currentBranch = branch
    do( "git merge %s" % trackedBranch )
  if currentBranch != wBranch:
    print "Reverting to working branch %s" % wBranch
    do( "git checkout %s" % wBranch )

def execPromote():
  if do( "git diff-index HEAD" ):
    print "Your working space is dirty. Commit first all changes!"
    sys.exit( 1 )
  refs = getRefs( defaultCurrent = True )
  for branch in refs:
    print "Promoting %s" % branch
    if not do( "git push origin %s:%s" % ( branch, branch ), checkValid = True ):
      print "Cannot push branch to origin"
      sys.exit( 1 )
  print "Sent %s to origin" % ", ".join( refs )


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
if parseRes.fforward:
  doneStuff = True
  execFForward()
if parseRes.promote:
  doneStuff = True
  execPromote()

if not doneStuff:
  parser.print_help()
  sys.exit( 1 )
