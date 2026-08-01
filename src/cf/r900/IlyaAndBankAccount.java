package cf.r900;

/*
 *  Ilya and Bank Account
 *  rating 900  |  tags: implementation, number theory
 *  https://codeforces.com/problemset/problem/313/A
 *  created 2026-08-01
 */

import java.io.*;
import java.util.*;

public class IlyaAndBankAccount {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();

        // TODO: read input and solve
        // int n = Integer.parseInt(br.readLine().trim());
        int n = Integer.parseInt(br.readLine().trim());
        if (n >= 0) System.out.println(n);
        else {
            int p = n / 10;
            int q = (n / 100) * 10 + n % 10;
            System.out.println(Math.max(p, q));
        }
        System.out.print(sb);
    }
}
