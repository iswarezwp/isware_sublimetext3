import sublime
import sublime_plugin


class IswareDoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        s = sublime.load_settings("isware.sublime-settings")
        first_name = s.get('first_name', 'Noname')
        self.view.insert(edit, 0, "Hi %s!" % first_name)
