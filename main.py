from PIL import Image
from sys import argv
import ffmpeg
import os
import cv2 as cv
import shutil

# TODO Use command line arguments instead of hardcoded input path
# TODO Make file paths fully compatible with Windows file system
# TODO Automatically compress with heatshrink when conversion is done

# Get user videos
in_video = "video.mp4"
out_video = os.path.join(os.path.dirname("./.temp/"), "temp.mp4")

# Create directiry if unavailable
directories = ["./.temp/", "./.temp/frames", "./output/"]

for directory in directories:
    if not os.path.exists(directory):
        os.mkdir(directory)


def resize(input, width, height, overwrite=False):
    print("Resizing video...")
    input = ffmpeg.input(input)
    out_video = os.path.join(os.path.dirname("./.temp/"), "temp.mp4")
    video = (input
             .filter('scale', width, height)
             .output(out_video)
             .overwrite_output()
             .run())
    return out_video


def convert_frames(video):
    print("Converting video into frames...")
    cv2Capture = cv.VideoCapture(video)
    cv2Output = os.path.dirname("./.temp/frames/")
    frameNr = 0

    while (True):
        successful, frame = cv2Capture.read()
        if successful:
            cv.imwrite(os.path.join(cv2Output, f'frame_{frameNr}.png'), frame)
        else:
            break
        frameNr += 1


def compress_to_bin(filename):
    im = Image.open(filename).convert(
        mode="L").point(lambda i: i > 127 and 255)

    imdata = list(im.getdata())

    imbit = []
    b_count = 0
    c8 = 0
    for c in imdata[:]:
        c8 = c8 << 1
        if c != 0:
            c8 = c8 | 1
        b_count += 1
        if b_count == 8:
            b_count = 0
            imbit.append(c8)
            c8 = 0

    # ENCODE
    im_comp = []
    c_m1 = imbit[0]
    runlength = 0
    for c in imbit[1:]:
        if runlength == 0:
            if c_m1 in [0, 255]:
                if c_m1 == c:
                    runlength = 2
                else:
                    im_comp.append(c_m1)
            else:
                # encode directly
                im_comp.append(c_m1)
                if c_m1 in [0x55, 0xaa]:
                    im_comp.append(0)
        else:
            if c_m1 == c:
                runlength += 1
            else:
                if runlength == 2:
                    im_comp.append(c_m1)
                    im_comp.append(c_m1)
                else:
                    if c_m1 == 0:
                        im_comp.append(0x55)
                    else:
                        im_comp.append(0xaa)
                    if runlength <= 127:
                        im_comp.append(runlength)
                    else:
                        im_comp.append((runlength & 0x7f) | 128)
                        im_comp.append(runlength >> 7)
                runlength = 0
        c_m1 = c

    if runlength == 0:
        im_comp.append(c_m1)
    else:
        if runlength == 2:
            im_comp.append(c_m1)
            im_comp.append(c_m1)
        else:
            if c_m1 == 0:
                im_comp.append(0x55)
            else:
                im_comp.append(0xaa)
            if runlength <= 127:
                im_comp.append(runlength)
            else:
                im_comp.append((runlength & 0x7f) | 128)
                im_comp.append(runlength >> 7)
        runlength = 0

    # DECODE
    im_decomp = []
    runlength = -1
    c_to_dup = -1
    for c in im_comp[:]:
        if c_to_dup == -1:
            if c in [0x55, 0xaa]:
                c_to_dup = c
            else:
                im_decomp.append(c)
        else:
            if runlength == -1:
                if c == 0:
                    im_decomp.append(c_to_dup)
                    c_to_dup = -1
                elif (c & 0x80) == 0:
                    if c_to_dup == 0x55:
                        im_decomp.extend([0] * c)
                    else:
                        im_decomp.extend([255] * c)
                    c_to_dup = -1
                else:
                    runlength = c & 0x7f
            else:
                runlength = runlength | (c << 7)
                if c_to_dup == 0x55:
                    im_decomp.extend([0] * runlength)
                else:
                    im_decomp.extend([255] * runlength)
                c_to_dup = -1
                runlength = -1

    if len(imbit) != len(im_decomp):
        print("Decomp len fail!")
    else:
        for a, b in zip(imbit, im_decomp):
            if (b < 0) or (b > 255):
                print("Range to big")
            if a != b:
                print("Decomp fail")
                break
    return im_comp


convert_frames(resize(in_video, 128, 64))

print("Compressing video into a binary...")

# TODO Make file directory compatible with Windows file system
output_file = open("./output/video.bin", "wb")

frameNumber = len([entry for entry in os.listdir("./.temp/frames")
                   if os.path.isfile(os.path.join("./.temp/frames", entry))])

for frame in range(1, int(frameNumber)):
    file = "./.temp/frames/frame_{}".format(frame) + ".png"
    compressed_data = compress_to_bin(file)
    output_file.write(bytearray(compressed_data))

output_file.close()
shutil.rmtree("./.temp/")
print("Removing temporary files...")
print("Conversion is done, you proceed with heatshrink compression")
