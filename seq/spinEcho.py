import sys
sys.path.append('../marcos_client')
import numpy as np
import experiment as ex
#from local_config import fpga_clk_freq_MHz
import matplotlib.pyplot as plt
import pdb
st = pdb.set_trace

def spin_echo(self, plotSeq):
#                    plot_rx=True, init_gpa=False,
#                    dbg_sc=0.5, # set to 0 to avoid RF debugging pulses in each RX window, otherwise amp between 0 or 1
#                    lo_freq=0.2, # MHz
#                    rf_amp=1, # 1 = full-scale
#                    trs=1, 
#                    rf_pi2_duration=50, # us, rf pi/2 pulse length
#                    rf_pi_duration=None, # us, rf pi pulse length  - if None then automatically gets set to 2 * rf_pi2_duration
#
#                    # spin-echo properties
#                    echo_duration=2000, # us, time from the centre of one echo to centre of the next
#                    readout_duration=500, # us, time in the centre of an echo when the readout occurs
#                    rx_period=10/3, # us, 3.333us, 300 kHz rate
#                    # (must at least be longer than readout_duration + trap_ramp_duration)
#                    ):
    init_gpa=True                   
#    dbg_sc=self.dbg_sc
    lo_freq=self.lo_freq
    rf_amp=self.rf_amp
    trs=self.trs
    rf_pi_duration=None
    rf_pi2_duration=self.rf_pi2_duration
    echo_duration=self.echo_duration
    readout_duration=self.readout_duration
    rx_period=self.rx_period
                     
    """
    readout gradient: x
    phase gradient: y
    slice/partition gradient: z
    """
    
    tr_pause_duration=2000
    echos_per_tr=1 # number of spin echoes (180 pulses followed by readouts) to do
                    
    if rf_pi_duration is None:
        rf_pi_duration = 2 * rf_pi2_duration

    # create appropriate waveforms for each echo, based on start time, echo index and TR index
    # note: echo index is 0 for the first interval (90 pulse until first 180 pulse) thereafter 1, 2 etc between each 180 pulse
    def rf_wf(tstart, echo_idx):
        pi2_phase = 1 # x
        pi_phase = 1j # y
        if echo_idx == 0:
            # do pi/2 pulse, then start first pi pulse
            return np.array([tstart + (echo_duration - rf_pi2_duration)/2, tstart + (echo_duration + rf_pi2_duration)/2,
                             tstart + echo_duration - rf_pi_duration/2]), np.array([pi2_phase, 0, pi_phase]) * rf_amp
        elif echo_idx == echos_per_tr:
            # finish final RF pulse
            return np.array([tstart + rf_pi_duration/2]), np.array([0])
        else:
            # finish last pi pulse, start next pi pulse
            return np.array([tstart + rf_pi_duration/2, tstart + echo_duration - rf_pi_duration/2]), np.array([0, pi_phase]) * rf_amp

    def tx_gate_wf(tstart, echo_idx):
        tx_gate_pre = 2 # us, time to start the TX gate before each RF pulse begins
        tx_gate_post = 1 # us, time to keep the TX gate on after an RF pulse ends

        if echo_idx == 0:
            # do pi/2 pulse, then start first pi pulse
            return np.array([tstart + (echo_duration - rf_pi2_duration)/2 - tx_gate_pre,
                             tstart + (echo_duration + rf_pi2_duration)/2 + tx_gate_post,
                             tstart + echo_duration - rf_pi_duration/2 - tx_gate_pre]), \
                             np.array([1, 0, 1])
        elif echo_idx == echos_per_tr:
            # finish final RF pulse
            return np.array([tstart + rf_pi_duration/2 + tx_gate_post]), np.array([0])
        else:
            # finish last pi pulse, start next pi pulse
            return np.array([tstart + rf_pi_duration/2 + tx_gate_post, tstart + echo_duration - rf_pi_duration/2 - tx_gate_pre]), \
                np.array([0, 1])

    def readout_wf(tstart, echo_idx):
        if echo_idx != 0:
            return np.array([tstart + (echo_duration - readout_duration)/2, tstart + (echo_duration + readout_duration)/2 ]), np.array([1, 0])
        else:
            return np.array([tstart]), np.array([0]) # keep on zero otherwise

    expt = ex.Experiment(lo_freq=lo_freq, rx_t=rx_period, init_gpa=init_gpa, gpa_fhdo_offset_time=(1 / 0.2 / 3.1))
    # gpa_fhdo_offset_time in microseconds; offset between channels to
    # avoid parallel updates (default update rate is 0.2 Msps, so
    # 1/0.2 = 5us, 5 / 3.1 gives the offset between channels; extra
    # 0.1 for a safety margin))

    global_t = 20 # start the first TR at 20us

    for tr in range(trs):
        for echo in range(echos_per_tr + 1):
            tx_t, tx_a = rf_wf(global_t, echo)
            tx_gate_t, tx_gate_a = tx_gate_wf(global_t, echo)
            readout_t, readout_a = readout_wf(global_t, echo)
            rx_gate_t, rx_gate_a = readout_wf(global_t, echo)

            global_t += echo_duration

            expt.add_flodict({
                'tx0': (tx_t, tx_a),
                'rx0_en': (readout_t, readout_a),
                'tx_gate': (tx_gate_t, tx_gate_a),
                'rx_gate': (rx_gate_t, rx_gate_a),
            })

        global_t += tr_pause_duration
        
    if plotSeq==1:
        expt.plot_sequence()
        plt.show()
        expt.__del__()
    elif plotSeq==0:
        rxd, msgs = expt.run()
        expt.__del__()
        return rxd['rx0'].real, msgs


