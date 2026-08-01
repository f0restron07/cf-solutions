/*
 *  HQ9+
 *  rating 900  |  tags: implementation
 *  https://codeforces.com/problemset/problem/133/A
 *  created 2026-08-01
 */

import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();

        // TODO: read input and solve
        // int n = Integer.parseInt(br.readLine().trim());
        String s=br.read();
        int n=s.length();
        for(int i=0;i<n;i++){
            if(s.charAt(i)=='H'||s.charAt(i)=='Q'||s.charAt(i)=='+'||s.charAt(i)=='99'){
                System.out.println("YES");
                break;
            }
        }
        System.out.print("NO");
    }
}
