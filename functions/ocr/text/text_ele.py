class BasicTextElement:
    def get_attrib_str(self, attrib_list, sep=","):
        """
        Get attribute string given attribute list
        """
        _attr_list = []
        for attrib in attrib_list:
            attr = str(self.get_attrib(attrib))
            if attr == "None":
                attr = "*"
            _attr_list.append(attr)
        return sep.join(_attr_list)

    def set_attrib(self, attrib_name, attrib_value):
        """
        Set attribute
        """
        self.__dict__[attrib_name] = attrib_value

    def get_attrib(self, attrib_name):
        """
        Get attribute value GIVEN attribute name
        """
        return self.__dict__[attrib_name] if attrib_name in self.__dict__ else "NA"
