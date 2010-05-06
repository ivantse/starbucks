import string, os, sys
import xml.dom.minidom
from xml.dom.minidom import Node

# functions used for reading configuration data from the config/* files
globals()["release_dir"] = "\\\\smfs01\\sm\\builds\\releases" 



#-----------------------------------------------------------------------------------------------------
# returns a dictionary of config info
def read_user_config():
	config = {}

	# default values for workspace locations is relative to starbucks in /starbucks/brew and /starbucks/j2me
	config["workspace_brew"] = os.path.normpath("brew")
	config["workspace_j2me"] = os.path.normpath("j2me")

	if not os.path.exists("config/config.xml"):
		# no config exists, return default values
		return config

	xmldoc = xml.dom.minidom.parse("config/config.xml")

	for workspace in xmldoc.getElementsByTagName("workspaces"):
		brews = workspace.getElementsByTagName("brew")
		j2mes = workspace.getElementsByTagName("j2me")

		config["workspace_brew"] = os.path.normpath(string.strip(brews[0].firstChild.data))
		config["workspace_j2me"] = os.path.normpath(string.strip(j2mes[0].firstChild.data))

	return config

#-----------------------------------------------------------------------------------------------------
def read_config(platform):
	if platform == "BREW":
		xmldoc = xml.dom.minidom.parse("config/brew_repositories.xml")
	else:
		xmldoc = xml.dom.minidom.parse("config/j2me_repositories.xml")

	projects = {}

	for proj in xmldoc.getElementsByTagName("project"):
		names = proj.getElementsByTagName("name")
		locs  = proj.getElementsByTagName("location")
		deps  = proj.getElementsByTagName("depends")
		dirnames = proj.getElementsByTagName("dirname")
		descs = proj.getElementsByTagName("description")
		builders = proj.getElementsByTagName("builders")

		name = string.strip(names[0].firstChild.data)
		loc  = string.strip(locs[0].firstChild.data)

		# get tag/branch from location tag
		if locs[0].getAttribute("tag") != "":
			rev = locs[0].getAttribute("tag")
		elif locs[0].getAttribute("branch") != "":
			rev = locs[0].getAttribute("branch")
		else:
			rev = ""

		if locs[0].getAttribute("cvsroot") != "":
			dl_method = "cvs"
			cvs_repository = loc
			cvs_username = os.environ['USERNAME']
			cvs_root = ':ext:'+cvs_username+'@'+locs[0].getAttribute("cvsroot")
			dl_info = [cvs_root, loc, rev]
		else:
			dl_method = "svn"
			dl_info = [loc, rev]

		if deps != []:
			dep = string.strip(deps[0].firstChild.data)
		else:
			dep = ""

		if dirnames != []:
			dirname = string.strip(dirnames[0].firstChild.data)
		else:
			dirname = string.lower(name)

		if descs != []:
			desc = string.strip(descs[0].firstChild.data)
		else:
			desc = ""

		builder_info = {}
		if builders != []:
			if builders[0].getAttribute("style") != "":
				style = builders[0].getAttribute("style")
				
				if style == "custom":
					builder_info["style"] = "custom"

					# get each builder size
					sml = builders[0].getElementsByTagName("small")
					med = builders[0].getElementsByTagName("medium")
					lrg = builders[0].getElementsByTagName("large")

					if sml != []:
						builder_info_sml = {}
						sml_local = (sml[0].getElementsByTagName("local"))[0].getAttribute("command")
						sml_release = (sml[0].getElementsByTagName("release"))[0].getAttribute("command")
						sml_nightly = (sml[0].getElementsByTagName("nightly"))[0].getAttribute("command")
						builder_info_sml["local"] = sml_local
						builder_info_sml["release"] = sml_release
						builder_info_sml["nightly"] = sml_nightly
						builder_info["small"] = builder_info_sml

					if med != []:
						builder_info_med = {}
						med_local = (med[0].getElementsByTagName("local"))[0].getAttribute("command")
						med_release = (med[0].getElementsByTagName("release"))[0].getAttribute("command")
						med_nightly = (med[0].getElementsByTagName("nightly"))[0].getAttribute("command")
						builder_info_med["local"] = med_local
						builder_info_med["release"] = med_release
						builder_info_med["nightly"] = med_nightly
						builder_info["medium"] = builder_info_med

					if lrg != []:
						builder_info_lrg = {}
						lrg_local = (lrg[0].getElementsByTagName("local"))[0].getAttribute("command")
						lrg_release = (lrg[0].getElementsByTagName("release"))[0].getAttribute("command")
						lrg_nightly = (lrg[0].getElementsByTagName("nightly"))[0].getAttribute("command")
						builder_info_lrg["local"] = lrg_local
						builder_info_lrg["release"] = lrg_release
						builder_info_lrg["nightly"] = lrg_nightly
						builder_info["large"] = builder_info_lrg
				else:
					builder_info["style"] = "standard"
			else:
				builder_info["style"] = "standard"
		else:
			# no information for the builder
			builder_info["style"] = "standard"
		
		#print "STYLE is: " + builder_info["style"] + " (" + name + ")"

		if builder_info["style"] == "standard":
			if builders != []:
				vers = builders[0].getElementsByTagName("vs_version")
				publish_dir = builders[0].getElementsByTagName("publish_dir")
				mks = builders[0].getElementsByTagName("makefile")

				if vers:
					builder_info["vs_version"] = vers[0].firstChild.data
				else:
					# default visual studio version is 8
					builder_info["vs_version"] = 8

				if publish_dir:
					builder_info["publish_dir"] = publish_dir[0].firstChild.data
				else:
					# if we haven't specified publish_dir then default to release dir for brew
					builder_info["publish_dir"] = globals()["release_dir"] + "\\brew\\" + name

				if mks:
					builder_info["makefile"] = mks[0].firstChild.data
				else:
					# standard makefile is Makefile.starbucks if not specified
					builder_info["makefile"] = "Makefile.starbucks"
			else:
				# defaults
				builder_info["vs_version"] = 8
				builder_info["publish_dir"] = globals()["release_dir"] + "\\brew\\" + name
				builder_info["makefile"] = "Makefile.starbucks"

		if projects.has_key(string.lower(name)):
			# ERROR: duplicate entries!
			print
			print "*******************************************"
			print "ERROR: DUPLICATE ENTRY IN CONFIGRATION FILE"
			print "Duplicate Project Name: " + string.lower(name)
			print "*******************************************"
			print
			sys.exit(2)

		if platform == "BREW":
			jproj = proj.getElementsByTagName("j2me_project")
			if jproj != []:
				j = string.strip(jproj[0].firstChild.data)
			else:
				j = ""

			# put in as lower-case so they can be retrieved with just lower-case key
			projects[string.lower(name)] = {}
			p = projects[string.lower(name)]
			p["name"] = name
			p["dep"] = dep
			p["dirname"] = dirname
			p["dl_method"] = dl_method
			p["dl_info"] = dl_info
			p["desc"] = desc
			p["j"] = j
			p["builder_info"] = builder_info
		else:
			projects[string.lower(name)] = {}
			p = projects[string.lower(name)]
			p["name"] = name
			p["dep"] = dep
			p["dirname"] = dirname
			p["dl_method"] = dl_method
			p["dl_info"] = dl_info
			p["desc"] = desc
	
	return projects

