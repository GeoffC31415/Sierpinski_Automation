# Sierpinski_Automation

Code for the second vivarium.

Run `Monitor.py` as root, and it will handle heating and lighting.

Lights driven via hardware PWM on pin 18 - requires wiringpi. Follows a scaled sine-cubed curve which looks reasonable due the capacitive buffering on the LED lightstrip (short bursts of power take more current as caps are at lower voltage - higher than expected brightness at low power-on proportions).

Temperatures are from ADC 4x inputs via thermistors on a voltage divider. Very sensitive to electronic noise. Median of the four sensor readings is what is taken as viv temperature, target is a sine wave which is configurable in the initial settings dictionary in `Monitor.py`.

Heating driven on two relays - currently a ceramic bulb.
