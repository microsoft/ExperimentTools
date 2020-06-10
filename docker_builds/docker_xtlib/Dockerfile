FROM pytorch-cuda

# add XTLib
RUN pip install --upgrade XTLib

# add ~/.data and ensure we can write to it
RUN sudo mkdir ~/.data
RUN sudo chown -R user:user ~/.data
