import os, string, sys, getopt, signal, getpass
import pysvn
import config


def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
	except getopt.GetoptError:
		print "GetoptError!"
		# print help information and exit
		usage()
		sys.exit()

	if len(args) == 1 and string.lower(args[0]) == "update":
		self_update()
		sys.exit()
	else:
		# always self-update anyways to stay up to date
		self_update()
	
	if len(args) < 2:
		print "Not enough arguments"
		usage()
		sys.exit()

	for o in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit()
	
	platform = string.upper(args[0])

	if platform not in ("J2ME", "BREW"):
		usage()
		sys.exit()

	# check if we're running windows, then we use CVSNT
	if sys.platform == "win32":
		#globals()["cvs_cmd"] = "contrib\CVSNT\cvs.exe"
		globals()["cvs_cmd"] = "contrib\cvs_chenv.bat"
	else:
		globals()["cvs_cmd"] = "cvs"

	globals()["brew_projects"] = config.read_config("BREW")
	globals()["j2me_projects"] = config.read_config("J2ME")
	globals()["user_config"] = config.read_user_config()
	globals()["fetch_stack_height"] = 0

	# FIXME: error check here?
	proj_name = args[1]

	if string.lower(proj_name) == ("list" or "menu"):
		print_available_projects(platform)
		sys.exit()

	this_proj = get_project(string.lower(proj_name), platform)

	if this_proj == "":
		print "Project not found, please check config files"
		sys.exit()

	print
	print "===================================================="
	print
	print "          Hello, welcome to Starbucks!"
	print
	print "===================================================="
	print
	print "*** initiating fetch:", proj_name, "("+platform+")", "***"
	print

	print "----------------------------------------------------"
	fetch_project(this_proj, platform)
	print "----------------------------------------------------"
#-----------------------------------------------------------------------------------------------------

def fetch_project(proj, platform):
	# don't allow circular dependencies!
	if globals()["fetch_stack_height"] > 20:
		print
		print "***"
		print "*** ERROR: There are too many dependencies! (circular dependencies?) ***"
		print "***"
		sys.exit()
	else:
		globals()["fetch_stack_height"] += 1

	# if this is a brew project, let's also download the j2me project and its deps
	if platform == "BREW":
		print "*** fetching J2ME equivalent project for BREW (if exists) ***"
		brew_fetch_j2me_project(proj)

	# get any dependencies this project needs
	fetch_deps(proj, platform)

	proj_name = get_name(proj)
	dirname = get_dirname(proj)

	if dirname == "":
		dirname = proj_name

	if platform == "BREW":
		user_config = globals()["user_config"]
		brew_workspace = user_config["workspace_brew"]

		# make directory just in case it isn't there
		if not os.path.exists(brew_workspace):
			os.makedirs(brew_workspace)
		path = brew_workspace+'/'+dirname
	else:
		user_config = globals()["user_config"]
		j2me_workspace = user_config["workspace_j2me"]

		# make directory just in case it isn't there
		if not os.path.exists(j2me_workspace):
			os.makedirs(j2me_workspace)
		path = j2me_workspace+'/'+dirname

	rev = get_revision(proj)

	# if already exists then update (clean), otherwise check it out
	if os.path.exists(path):
		print "updating: ", proj_name
		if get_dl_method(proj) == "cvs":
			cvs_root = get_cvs_root(proj)
			cvs_update(cvs_root, rev, path)
		else:
			svn_update(path, rev)
	else:
		print "fetching: ", proj_name
		if get_dl_method(proj) == "cvs":
			cvs_root = get_cvs_root(proj)
			cvs_repository = get_cvs_repository(proj)
			cvs_checkout(cvs_root, cvs_repository, rev, path)
		else:
			svn_url = get_location(proj)
			svn_checkout(svn_url, rev, path)

#-----------------------------------------------------------------------------------------------------
def fetch_deps(proj, platform):
	if get_dependencies(proj) == "":
		return

	# otherwise, we have dependencies, let's go download those
	print "*** dependency required: ", get_dependencies(proj), "(for", get_name(proj)+")", "***"
	dep_proj = get_project(string.lower(get_dependencies(proj)), platform)
	fetch_project(dep_proj, platform)

#-----------------------------------------------------------------------------------------------------
def brew_fetch_j2me_project(proj):
	# get the j2me project name
	j2me_proj = get_j2me_project_name(proj)

	j = get_project(string.lower(j2me_proj), "J2ME")

	if j2me_proj is not "":
		if j is not "":
			print "*** fetching J2ME project: ", get_name(j), "***"
			fetch_project(j, "J2ME")

#-----------------------------------------------------------------------------------------------------
def get_project(proj_name, platform):
	if platform == "BREW":
		if globals()["brew_projects"].has_key(proj_name):
			return brew_projects[proj_name]
		return ""
	else:
		if globals()["j2me_projects"].has_key(proj_name):
			return j2me_projects[proj_name]
		return ""

#-----------------------------------------------------------------------------------------------------
def get_name(proj):
	return proj["name"]

def get_dependencies(proj):
	return proj["dep"]

def get_dirname(proj):
	return proj["dirname"]

def get_dl_method(proj):
	return proj["dl_method"]

def get_dl_info(proj):
	return proj["dl_info"]

def get_cvs_root(proj):
	info = get_dl_info(proj)
	return info[0]

def get_cvs_repository(proj):
	return get_location(proj)

def get_location(proj):
	if get_dl_method(proj) == "cvs":
		info = get_dl_info(proj)
		return info[1]
	else:
		info = get_dl_info(proj)
		return info[0]

def get_revision(proj):
	if get_dl_method(proj) == "cvs":
		info = get_dl_info(proj)
		return info[2]
	else:
		info = get_dl_info(proj)
		return info[1]

def get_description(proj):
	return proj["desc"]

def get_j2me_project_name(proj):
	return proj["j"]

#-----------------------------------------------------------------------------------------------------
def usage():
	print "Fetcher v1.1"
	print "USAGE: fetcher <platform> <project|list|menu>"

#-----------------------------------------------------------------------------------------------------
def print_available_projects(platform):
	print
	print "Available", string.upper(platform), "Projects:"
	print "------------------------"
	platform_projects = globals()[string.lower(platform)+"_projects"]

	projects = {}

	for key, value in platform_projects.iteritems():
		projects[get_name(value)] = get_description(value)

	ordered_names = projects.keys()
	ordered_names.sort()

	longest_name_len = 0
	for name in ordered_names:
		if len(name) > longest_name_len:
			longest_name_len = len(name)
	
	for name in ordered_names:
		printed_name = name + "    "
		for i in range (len(name), longest_name_len):
			printed_name = printed_name + " "

		print "  ", printed_name, projects[name]

#-----------------------------------------------------------------------------------------------------
def self_update():
	print
	print "Self-updating starbucks..."

	svn_update("config", "")

	print "\bdone."

#-----------------------------------------------------------------------------------------------------
def svn_cancel():
	#sys.stdout.write('.')
	return globals()["svn_interrupted"]

def svn_notify( event_dict ):
	globals()["svn_tick"] += 1


	if event_dict['action'] == pysvn.wc_notify_action.update_add:
		print event_dict['path']
	elif event_dict['action'] == pysvn.wc_notify_action.update_update:
		if svn_tick % 7 == 0:
			sys.stdout.write("\b|")
		elif svn_tick % 7 == 1:
			sys.stdout.write("\b/")
		elif svn_tick % 7 == 2:
			sys.stdout.write("\b-")
		elif svn_tick % 7 == 3:
			sys.stdout.write("\b\\")
		elif svn_tick % 7 == 4:
			sys.stdout.write("\b|")
		elif svn_tick % 7 == 5:
			sys.stdout.write("\b/")
		elif svn_tick % 7 == 6:
			sys.stdout.write("\b-")
		#print event_dict['path']

	#if event_dict['action'] == pysvn.wc_notify_action.delete:
        #	sys.stdout.write("Removing %s\n" % (event_dict['path']))
    	#elif event_dict['action'] == pysvn.wc_notify_action.add:
        #	sys.stdout.write("Adding %s\n" % (event_dict['path']))
    	#elif event_dict['action'] == pysvn.wc_notify_action.copy:
        #	sys.stdout.write("Copying %s\n" % (event_dict['path'])) 
	return

def svn_update(path, rev):
	client = pysvn.Client()
	client.callback_notify = svn_notify
	client.callback_cancel = svn_cancel
	client.callback_get_login = svn_login

	status_list = client.status(path)
	this_path = status_list[len(status_list) - 1]
	if this_path.is_locked:
		print "Working copy (local) at '"+path+"' is locked... cleaning up before update"
		client.cleanup(path)

	try:
		if rev != "":
			client.update(path)
		else:
			# get a tag/branch
			#revision = 
			#client.update(path, True, revision)
			# TODO/FIXME
			client.update(path)
	except pysvn.ClientError, e:
		print str(e)

def svn_checkout(svn_url, rev, path):
	client = pysvn.Client()
	client.callback_notify = svn_notify
	client.callback_cancel = svn_cancel
	client.callback_get_login = svn_login

	print " SVN URL: ", svn_url
	try:
		print " WORKING: ...... (please wait: the coffee is brewing)"
		if rev != "":
			client.checkout(svn_url, path)
		else:
			# get a specified tag/branch; THIS SHOULD NEVER HAPPEN WITH SVN; already embedded in URL, RIGHT?
			client.checkout(svn_url, path)
	except pysvn.ClientError, e:
		print str(e)

def svn_login(realm, username, may_save):
	retcode = True
	user = getpass.getuser()
	password = getpass.getpass(user+"'s SVN password:")

	return retcode, user, password, may_save

#-----------------------------------------------------------------------------------------------------
def cvs_update(cvs_root, rev, path):
	real_path = path
	if sys.platform == "win32":
		real_path = string.replace(path, '/', '\\')

	if rev == "":
		print "updating:", real_path
		cvs_command = globals()["cvs_cmd"] +' '+cvs_root+' update '+real_path
		os.system(cvs_command)
	else:
		# updating to branch/tag
		print "updating:", real_path, "(REV:", rev+")"
		cvs_command = globals()["cvs_cmd"] +' '+cvs_root+' update -r '+rev+' '+real_path
		os.system(cvs_command)

def cvs_checkout(cvs_root, cvs_repository, rev, path):
	real_path = path
	if sys.platform == "win32":
		real_path = string.replace(path, '/', '\\')
	
	if rev == "":
		print "checking out:", cvs_root+':'+cvs_repository, "to", real_path
		cvs_command = globals()["cvs_cmd"] +' '+cvs_root+' co -d '+real_path+' '+cvs_repository
		os.system(cvs_command)
	else:
		# get a branch/tag
		print "checking out:", cvs_root+':'+cvs_repository, " (REV:", rev+") to", real_path
		cvs_command = globals()["cvs_cmd"] +' '+cvs_root+' co -r '+rev+' -d '+real_path+' '+cvs_repository
		os.system(cvs_command)

#-----------------------------------------------------------------------------------------------------
def handler(signum, frame):
	if signum == signal.SIGINT:
		globals()["svn_interrupted"] = True
		#print "Signal handler called with signal", signum
		#raise IOError, "Couldn't finish!"
		print "*** USER CANCELLED REQUEST ***"
		sys.exit()
	
#-----------------------------------------------------------------------------------------------------
if __name__ == "__main__":
	globals()["svn_interrupted"] = False
	globals()["svn_tick"] = 0
	signal.signal(signal.SIGINT, handler)
	main()
