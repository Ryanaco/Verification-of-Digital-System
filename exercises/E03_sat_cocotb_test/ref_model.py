#
# Sat. Filter Reference Model
#


class sat_filter_ref_model():
    """ Saturation Filter Reference Model.
    """

    def __init__(self, data_w = 4, threshold = 8) -> None:
        """ Class constructor."""
        self.data_w = data_w
        self.threshold = threshold

        self.signal_data_in = 0
        self.signal_valid_in = 0
        self.signal_data_out = 0
        self.signal_valid_out = 0
        self.signal_overflow = 0

    def operation(self, data_in) -> int:
        """ Saturation Filter operation. """

        self.signal_data_in = data_in

        if (data_in <= self.threshold):
            self.signal_data_out = self.signal_data_in
            self.signal_valid_out = 1
        else:
            self.signal_data_out = self.threshold
            self.signal_valid_out = 1
            self.signal_overflow = 1

        return self.signal_data_out