def print_critical(original: str):
    with open(original, 'r', encoding='utf-8') as f:
        only_critical = [line for line in f.readlines() if 'CRITICAL' in line]

    with open(original + '.critical', 'w') as f:
        f.write(''.join(only_critical))


def main():
    print_critical(r'C:\Users\wjjo\Desktop\5MA상향돌파일부.txt')


if __name__ == '__main__':
    main()
