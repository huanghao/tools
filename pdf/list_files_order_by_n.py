import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="+")
    return parser.parse_args()


def main():
    args = parse_args()
    filenames = args.filenames

    filtered_filenames = []
    for filename in filenames:
        basename = os.path.basename(filename)
        key = os.path.splitext(basename)[0]
        if not key.isdigit():
            continue

        filtered_filenames.append((key, filename))

    filtered_filenames.sort(key=lambda x: int(x[0]))

    for key, filename in filtered_filenames:
        print(filename)


if __name__ == "__main__":
    main()
