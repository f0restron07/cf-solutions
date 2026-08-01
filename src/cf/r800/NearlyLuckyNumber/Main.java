/*
 *  Nearly Lucky Number
 *  rating 800  |  tags: implementation
 *  https://codeforces.com/problemset/problem/110/A
 *  created 2026-07-27
 */

import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();
        int n=br.readLine();
        
        // TODO: read input and solve
        // int n = Integer.parseInt(br.readLine().trim());
        String s=br.readLine().trim();
        int c=0;
        for(int i=0;i<s.length();i++)if(s.charAt(i)=='4'||s.charAt(i)=='7')c++;
        System.out.print(c==4||c==7?"YES":"NO");

        System.out.print(sb);
    }
}
