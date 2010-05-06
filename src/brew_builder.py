import getopt, sys, string, shutil, glob
import config
import os

def main():
	globals()["all_projects"] = get_projects()

	try:
		opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
	except getopt.GetoptError:
		# print help information and exit:
		usage()
		sys.exit(2)

	if len(args) < 3:
		usage()
		sys.exit(2)

	for o in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit(2)

	project    = string.lower(args[0])
	build_size = string.lower(args[1])
	build_type = string.lower(args[2])
	build_version = ""

	all_projects = globals()["all_projects"]
	if project not in all_projects:
		project_not_found(project)
		sys.exit(1)


	if build_size not in ("small", "medium", "large"):
		sb_print("ERROR: build size argument must be small, medium, or large")
		usage()
		sys.exit(2)

	if build_type not in ("local", "nightly", "release"):
		sb_print("ERROR: build type argument must be LOCAL, NIGHTLY or RELEASE")
		usage()
		sys.exit(2)
	elif string.lower(build_type) == "release":
		if len(args) < 4:
			sb_print("ERROR: missing version argument for release")
			usage()
			sys.exit(2)

		build_version = args[3]

	if sys.platform == "win32":
		globals()["make_cmd"] = "..\..\contrib\BREW\make_chenv.bat"
	else:
		# FIXME
		globals()["make_cmd"] = "make"

	# this is a stack of return values from building; it will be used to construct the report
	globals()["build_rets"] = []
	build_rets = globals()["build_rets"]

	ret = build_project(project, build_size, build_type)
	if ret != 0:
		build_failed()
	build_ret = {"name":project, "ret":ret}
	build_rets.append(build_ret)

	if build_type in ("nightly", "release"):
		all_projects = globals()["all_projects"]
		project_obj = all_projects[project]
		builder_info = get_builder_info(project_obj)

		# only publish when using standard style
		# FIXME, don't publish when autopublish=false, or allow autopublish=true to allow custom style to publish with this too
		if builder_info["style"] == "standard":
			publish_dir = builder_info["publish_dir"]
			publish_build(project, build_size, build_type, publish_dir, build_version)
	
	show_report()

	if build_type == "release":
		print
		sb_print("REMINDER: Please remember to commit to QABUILDS.")
		sb_print("REMINDER: Please remember to TAG your release.")
		sb_print("REMINDER: Please remember to update BERPS.")
		sb_print("REMINDER: Please remember to update TestTrack Pro.")
		sb_print("REMINDER: Please remember to send a Build Release E-mail to QA.")
		sb_print("REMINDER: Please go drink a cup of coffee now while QA slaves over your build.")
		print
		sb_print("$$$ - Good Job! Another valiant effort by the DChoc BREW Team! - $$$")
		print

def usage():
	print
	print "BREW Builder v1.1"
	print "USAGE: brew_builder.py <project> <small|medium|large> <local|nightly|release> [version]"
	print
	print "Note: the version parameter is only used for the RELEASE build type using the STANDARD build style"
	print 
				
def project_not_found(project):
	print
	sb_print("*** ERROR: Could not find project to build: " + project + " ***")
	sb_print("Please type \"ORDER BREW LIST\" to see the list of all available BREW projects")

def get_projects():
	# get list of projects
	return config.read_config("BREW")

def build_project(project, build_size, build_type):

	# build project dependencies
	compile_deps(project, build_size, build_type)

	# setup builder info
	all_projects = globals()["all_projects"]
	project_obj = all_projects[project]
	builder_info = get_builder_info(project_obj)

	# if we have builder info
	if builder_info:
		build_style = builder_info["style"]

		#print "BUILD_STYLE: " + build_style + " (" + project + ")"

		if build_style == "custom":
			builder_info = builder_info[build_size]
		else:
			# standard
			build_style = "standard"
	else:
		sb_print("No builder info found: reverting to STANDARD")
		build_style = "standard"
	
	# nice white space for prettiness
	print

	# let's go into the project's directory to prepare for compiling
	proj_dir = project_obj["dirname"]
	newdir = "brew/"+proj_dir
	sb_print("Changing directory to: " + proj_dir)
	os.chdir(newdir)
	
	print

	build_ret = 0

	if build_style == "standard":
		vs_version = ""
		makefile = ""

		vs_version = builder_info["vs_version"]
		makefile = builder_info["makefile"]

		# standard build style
		build_ret = build_project_standard(makefile, build_size, vs_version)
	else:
		# if use custom build scripts then call build_project_custom
	 	build_ret = build_project_custom(builder_info, build_type)
	
	print

	# go back up to the "starbucks" directory
	os.chdir("../..")

	return build_ret

# build the project using starbucks' standard method
def build_project_standard(makefile, size, vs_version):
	sb_print("Building with STANDARD style")
	sb_print("============================")
	sb_print("Building project with:    " + makefile)
	make_cmd = globals()["make_cmd"]
	build_command = make_cmd + " " + makefile + " " + string.upper(size) + " " + vs_version
	sb_print("Executing command:        " + build_command)
	ret = os.system(build_command)
	if ret != 0:
		build_failed()
	print
	return ret

# only use this with standard build process; custom should handle its own publishing stuff
def publish_build(project, build_size, build_type, publish_dir, build_version):
	# let's go into the project's directory
	all_projects = globals()["all_projects"]
	project_obj = all_projects[project]

	proj_dir = project_obj["dirname"]
	newdir = "brew/"+proj_dir
	sb_print("Changing directory to: " + proj_dir)
	os.chdir(newdir)

	mods = "./build/arm_le/*.mod"
	dlls = "./build/win32/*.dll"

	final_dir = publish_dir + "\\nightly"

	if build_type == "release":
		# FIXME
		final_dir = publish_dir + "\\" + build_version
		sb_print("TODO: RELEASE not yet available")
	
	if build_size == "large":
		final_dir = final_dir + "\\lrg"
	elif build_size == "medium":
		final_dir = final_dir + "\\med"
	elif build_size == "small":
		final_dir = final_dir + "\\sml"

	sb_print("Publishing to OTA, type:     " + string.upper(build_type))
	sb_print("Publishing to Directory:     " + final_dir)

	final_dir_arm = final_dir + "\\arm_le"
	final_dir_win32 = final_dir + "\\win32"

	if not os.path.isdir(final_dir_arm):
		os.makedirs(final_dir_arm)

	if not os.path.isdir(final_dir_win32):
		os.makedirs(final_dir_win32)

	for file in glob.glob(mods):
		dest = final_dir_arm + "\\" + os.path.basename(file)
		shutil.copy(file, dest)
		sb_print("           Copying file:     " + file + " -> " + dest)

	for file in glob.glob(dlls):
		dest = final_dir_win32 + "\\" + os.path.basename(file)
		shutil.copy(file, dest)
		sb_print("           Copying file:     " + file + " -> " + dest)
	
	# copy resource files
	if build_size == "large":
		if not os.path.isdir("./build/lrg"):
			sb_print("*** ERROR: could not find resource directory: ./build/lrg ***")
			sys.exit(1)
		else:
			for file in glob.glob("./build/lrg/*"):
				# don't go down recursively
				if not os.path.isdir(file):
					shutil.copy(file, final_dir_arm)
					shutil.copy(file, final_dir_win32)
					sb_print("           Copying file:     " + file + " -> " + final_dir_arm)
					sb_print("           Copying file:     " + file + " -> " + final_dir_win32)

	elif build_size == "medium":
		if not os.path.isdir("./build/med"):
			sb_print("*** ERROR: could not find resource directory: ./build/med ***")
			sys.exit(1)
		else:
			for file in glob.glob("./build/med/*"):
				# don't go down recursively
				if not os.path.isdir(file):
					shutil.copy(file, final_dir_arm)
					shutil.copy(file, final_dir_win32)
					sb_print("           Copying file:     " + file + " -> " + final_dir_arm)
					sb_print("           Copying file:     " + file + " -> " + final_dir_win32)

	elif build_size == "small":
		if not os.path.isdir("./build/sml"):
			sb_print("*** ERROR: could not find resource directory: ./build/sml ***")
			sys.exit(1)
		else:
			for file in glob.glob("./build/sml/*"):
				# don't go down recursively
				if not os.path.isdir(file):
					shutil.copy(file, final_dir_arm)
					shutil.copy(file, final_dir_win32)
					sb_print("           Copying file:     " + file + " -> " + final_dir_arm)
					sb_print("           Copying file:     " + file + " -> " + final_dir_win32)
	
	os.chdir("..\..")

# build the project using custom (non-starbucks-standard) script
def build_project_custom(builder_info, build_type):
	if builder_info[build_type]:
		sb_print("Building with CUSTOM style")
		sb_print("==========================")
		sb_print("Executing command:        " + builder_info[build_type])
		ret = os.system(builder_info[build_type])
		print
		return ret
	else:
		sb_print("ERROR! Missing appropriate build information for CUSTOM style")
		sys.exit(1)

# compile the dependencies for a project
def compile_deps(project, size, type):
	sb_print("Checking for dependencies for: " + project)

	all_projects = globals()["all_projects"]
	project_obj = all_projects[project]
	dep = string.lower(project_obj["dep"])

	if dep == "":
		#print "NO DEPENDENCIES TO COMPILE"
		# no dependencies
		return

	sb_print("Found dependency: " + dep)
	ret = build_project(dep, size, type)

	build_rets = globals()["build_rets"]
	build_ret = {"name":dep, "ret":ret}
	build_rets.append(build_ret)

def get_builder_info(project_obj):
	builder_info = project_obj["builder_info"]
	return builder_info

def sb_print(str):
	print "[starbucks] " + str

def build_failed():
	sb_print("ERROR! This build has failed somewhere.")
	sb_print("Oops!")
	sys.exit(1)

def show_report():
	build_rets = globals()["build_rets"]
	print
	print
	sb_print("================ BUILD REPORT ================")
	print
	for ret_dict in build_rets:
		project = ret_dict["name"]
		ret = ret_dict["ret"]

		ret_string = "*** FAILED ***"
		if ret == 0:
			ret_string = "SUCCESS"

		# don't print status until 35 spaces from the left
		spacer = " "
		while (2 + len(project) + 4) + len(spacer) < 35:
			spacer = spacer + " "


		sb_print("  " + project + ":   " + spacer + ret_string)
	print
	sb_print("==============================================")

if __name__ == "__main__":
	main()
